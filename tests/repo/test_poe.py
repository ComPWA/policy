import io
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.repo.poe import (
    _check_expected_sections,
    _check_no_uv_run,
    _set_upgrade_task,
    _update_doclive,
    main,
)
from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject

_PYPROJECT = dedent("""
    [project]
    name = "my-package"
    classifiers = [
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ]

    [dependency-groups]
    dev = ["my-package"]
    doc = ["myst-nb", "sphinx-autobuild"]
    notebooks = ["jupyterlab"]

    [tool.poe.tasks.doc]
    cmd = "sphinx-build -b html docs docs/_build/html"

    [tool.poe.tasks.doclive]
    cmd = "sphinx-autobuild docs docs/_build/html"

    [tool.poe.tasks.docnb]
    cmd = "sphinx-build -b html docs docs/_build/html"

    [tool.poe.tasks.docnblive]
    cmd = "sphinx-autobuild docs docs/_build/html"

    [tool.poe.tasks.test]
    cmd = "pytest"

    [tool.poe.tasks.nb]
    cmd = "pytest --nbmake"

    [tool.poe.tasks.all]
    sequence = ["test", "doc"]

    [tool.tox]
    legacy_tox_ini = ""
""").lstrip()


@pytest.fixture
def poe_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_init: Callable[[Path], None],
    git_add: Callable[[Path], None],
) -> Path:
    git_init(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "conf.py").touch()
    (tmp_path / "docs" / "index.ipynb").touch()
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text(_PYPROJECT)
    git_add(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def describe_main():
    def configures_groups_and_tasks(poe_repo: Path):
        with pytest.raises(PrecommitError):
            main(has_notebooks=True, package_manager="uv")

        pyproject = (poe_repo / "pyproject.toml").read_text()
        assert "[tool.poe.executor]" in pyproject  # uv executor configured
        assert "[tool.poe.groups.doc.tasks.doc]" in pyproject  # doc migrated to group
        assert "[tool.poe.groups.test.tasks.test]" in pyproject
        assert "test-py310" in pyproject  # multi-version test-all tasks generated
        assert "test-py311" in pyproject
        assert "[tool.poe.tasks.upgrade]" in pyproject  # upgrade task added

    def uses_pixi_upgrade_command(poe_repo: Path):
        with pytest.raises(PrecommitError):
            main(has_notebooks=True, package_manager="pixi")

        pyproject = (poe_repo / "pyproject.toml").read_text()
        assert "pixi upgrade" in pyproject  # pixi-specific upgrade command

    def is_noop_without_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        main(has_notebooks=False, package_manager="uv")  # no pyproject.toml -> no-op


def describe_update_doclive():
    def adds_executor():
        # cspell:ignore autobuild
        config = dedent("""
            [dependency-groups]
            doc = ["sphinx-autobuild"]

            [tool.poe.groups.doc.tasks.doclive]
            cmd = "sphinx-autobuild docs docs/_build/html"
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Updated Poe the Poet doclive task"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _update_doclive(pyproject)
        result = pyproject.dumps()
        assert "sphinx-autobuild" in result
        assert "executor" in result


def describe_check_expected_sections():
    def reports_missing_tasks(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
    ):
        git_init(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "conf.py").touch()
        (tmp_path / "pyproject.toml").write_text("[tool.poe.tasks]\n")
        git_add(tmp_path)
        monkeypatch.chdir(tmp_path)
        pyproject = Pyproject.load()
        with pytest.raises(
            PrecommitError, match=r"missing task definitions: doc, doclive"
        ):
            _check_expected_sections(pyproject, has_notebooks=False)


def describe_check_no_uv_run():
    def rejects_uv_run():
        config = dedent("""
            [tool.poe.tasks.test]
            cmd = "uv run pytest"
        """).lstrip()
        pyproject = Pyproject.load(io.StringIO(config))
        with pytest.raises(PrecommitError, match=r"should not use 'uv run'"):
            _check_no_uv_run(pyproject)


def describe_set_upgrade_task():
    def removes_task_when_empty(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        config = dedent("""
            [tool.poe.tasks.upgrade]
            cmd = "outdated"
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Removed Poe the Poet upgrade task"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _set_upgrade_task(pyproject, package_manager="conda")
        assert "upgrade" not in pyproject.dumps()
