import io
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.python.ruff import (
    _move_ruff_lint_config,
    _update_lint_dependencies,
    check,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.session import Session

_PRECOMMIT_TO_CLEAN = dedent("""
    repos:
      - repo: https://github.com/psf/black
        rev: 24.1.0
        hooks:
          - id: black
      - repo: https://github.com/pycqa/flake8
        rev: 7.0.0
        hooks:
          - id: flake8
      - repo: https://github.com/nbQA-dev/nbQA
        rev: 1.8.0
        hooks:
          - id: nbqa-isort
""").lstrip()


@pytest.fixture
def ruff_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_init: Callable[[Path], None],
) -> Path:
    git_init(tmp_path)
    package = tmp_path / "src" / "my_package"
    package.mkdir(parents=True)
    (package / "__init__.py").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "conf.py").touch()
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# My Package\n\nText.\n")
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
        [project]
        name = "my-package"
        classifiers = [
            "Programming Language :: Python :: 3.10",
        ]

        [tool.black]
        line-length = 88

        [tool.ruff]
        select = ["E"]
        ignore = ["D203"]

        [tool.nbqa.addopts]
        ruff = ["--extend-ignore=E501"]
        """).lstrip()
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def describe_main():
    def migrates_config_with_notebooks(ruff_repo: Path, run_check):
        precommit = ModifiablePrecommit.load(io.StringIO(_PRECOMMIT_TO_CLEAN))
        with Session.load(precommit) as session:
            run_check(check, session, has_notebooks=True, imports_on_top=True)

        pyproject = (ruff_repo / "pyproject.toml").read_text()
        assert "[tool.black]" not in pyproject  # black settings removed
        assert "[tool.ruff.lint]" in pyproject  # linting config migrated
        assert 'select = ["ALL"]' in pyproject
        assert '"*.ipynb"' in pyproject  # per-file-ignores for notebooks

        config = precommit.dumps()
        assert "flake8" not in config  # flake8 hook removed
        assert "https://github.com/astral-sh/ruff-pre-commit" in config

    @pytest.mark.usefixtures("ruff_repo")
    def adds_ruff_format_without_notebooks(run_check):
        precommit = ModifiablePrecommit.load(io.StringIO(_PRECOMMIT_TO_CLEAN))
        with Session.load(precommit) as session:
            run_check(check, session, has_notebooks=False, imports_on_top=False)

        config = precommit.dumps()
        assert "https://github.com/astral-sh/ruff-pre-commit" in config
        assert "ruff-format" in config

    def migrates_legacy_config(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "pyproject.toml").write_text(
            dedent("""
            [project]
            name = "my-package"
            requires-python = ">=3.10"

            [tool.ruff]
            target-version = "py39"

            [tool.ruff.lint]
            extend-select = ["C90"]
            ignore = ["ANN101", "D203"]

            [tool.nbqa.addopts]
            black = ["--line-length=85"]
            flake8 = ["--ignore=E501"]
            isort = ["--profile=black"]
            """).lstrip()
        )
        monkeypatch.chdir(tmp_path)
        precommit = ModifiablePrecommit.load(io.StringIO("repos: []\n"))
        with Session.load(precommit) as session:
            run_check(check, session, has_notebooks=True, imports_on_top=False)

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert "target-version" not in pyproject  # dropped for requires-python
        assert "extend-select" not in pyproject  # folded into select
        assert "ANN101" not in pyproject  # deprecated rule removed


def describe_move_ruff_lint_config():
    def moves_settings_under_lint_table():
        config = dedent("""
            [tool.ruff]
            select = ["E", "F"]
            ignore = ["D203"]

            [tool.ruff.isort]
            known-first-party = ["my_package"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _move_ruff_lint_config(pyproject)
        assert any("Moved linting configuration" in m for m in pyproject.changelog)
        result = pyproject.dumps()
        assert "[tool.ruff.lint]" in result
        assert "[tool.ruff.lint.isort]" in result


def describe_update_lint_dependencies():
    def adds_ruff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        config = dedent("""
            [project]
            name = "my-package"
            classifiers = ["Programming Language :: Python :: 3.10"]
        """).lstrip()
        (tmp_path / "pyproject.toml").write_text(config)
        with Session() as session:
            pyproject = session.pyproject
            _update_lint_dependencies(session)
            assert pyproject is not None
            assert pyproject.changelog  # something changed
            assert "ruff" in pyproject.dumps()

    def pins_python_version_for_legacy_python(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        config = dedent("""
            [project]
            name = "my-package"
            classifiers = ["Programming Language :: Python :: 3.6"]
        """).lstrip()
        (tmp_path / "pyproject.toml").write_text(config)
        with Session() as session:
            pyproject = session.pyproject
            _update_lint_dependencies(session)
            assert pyproject is not None
            assert pyproject.changelog  # something changed
            result = pyproject.dumps()
        assert "python_version" in result
        assert "3.7.0" in result

    def is_noop_without_package_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[tool.foo]\nx = 1\n")
        with Session() as session:
            _update_lint_dependencies(session)
