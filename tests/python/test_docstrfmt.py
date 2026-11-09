from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.python.docstrfmt import check
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session


@pytest.fixture
def pyproject_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_init: Callable[[Path], None],
) -> Path:
    git_init(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "module.py").touch()
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "my-package"\n')
    return path


def describe_check():
    def adds_hook_and_settings(run_check, tmp_path: Path, pyproject_path: Path):
        path = tmp_path / ".pre-commit-config.yaml"
        path.write_text(
            dedent("""
            repos:
              - repo: https://github.com/pre-commit/pre-commit-hooks
                rev: v6.0.0
                hooks:
                  - id: check-yaml
            """).lstrip()
        )
        precommit = ModifiablePrecommit.load(path)
        with Session.load(precommit) as session:
            run_check(check, session, docstrfmt=True)

        assert "id: docstrfmt" in path.read_text()
        settings = pyproject_path.read_text()
        assert "[tool.docstrfmt]" in settings
        assert "docstring-trailing-line = false" in settings
        assert "format-python-code-blocks = false" in settings

    @pytest.mark.usefixtures("pyproject_path")
    @pytest.mark.parametrize(
        "hook_options",
        [
            "types: [python]",
            "types_or: [python]",
            "files: ^src/",
        ],
    )
    def removes_file_type_overrides(run_check, tmp_path: Path, hook_options: str):
        path = tmp_path / ".pre-commit-config.yaml"
        path.write_text(
            dedent(f"""
            repos:
              - repo: https://github.com/LilSpazJoekp/docstrfmt
                rev: v2.2.1
                hooks:
                  - id: docstrfmt
                    {hook_options}
            """).lstrip()
        )
        precommit = ModifiablePrecommit.load(path)
        with Session.load(precommit) as session:
            run_check(check, session, docstrfmt=True)

        result = path.read_text()
        assert hook_options not in result
        assert "rev: v2.2.1" in result

    def keeps_existing_settings(run_check, tmp_path: Path, pyproject_path: Path):
        pyproject_path.write_text(
            dedent("""
            [project]
            name = "my-package"

            [tool.docstrfmt]
            docstring-trailing-line = true
            format-python-code-blocks = false
            """).lstrip()
        )
        path = tmp_path / ".pre-commit-config.yaml"
        path.write_text(
            dedent("""
            repos:
              - repo: https://github.com/LilSpazJoekp/docstrfmt
                rev: v2.2.1
                hooks:
                  - id: docstrfmt
            """).lstrip()
        )
        original = pyproject_path.read_text()
        precommit = ModifiablePrecommit.load(path)
        with Session.load(precommit) as session:
            run_check(check, session, docstrfmt=True)

        assert not precommit.changelog
        assert pyproject_path.read_text() == original

    @pytest.mark.parametrize("disable", ["option", "no-python-files"])
    def removes_hook_and_settings(
        run_check, tmp_path: Path, pyproject_path: Path, disable: str
    ):
        if disable == "no-python-files":
            (tmp_path / "module.py").unlink()
        pyproject_path.write_text(
            dedent("""
            [project]
            name = "my-package"

            [tool.docstrfmt]
            docstring-trailing-line = false
            """).lstrip()
        )
        path = tmp_path / ".pre-commit-config.yaml"
        path.write_text(
            dedent("""
            repos:
              - repo: https://github.com/LilSpazJoekp/docstrfmt
                rev: v2.2.1
                hooks:
                  - id: docstrfmt
            """).lstrip()
        )
        precommit = ModifiablePrecommit.load(path)
        with Session.load(precommit) as session:
            run_check(check, session, docstrfmt=disable == "no-python-files")

        assert "docstrfmt" not in path.read_text()
        assert "docstrfmt" not in pyproject_path.read_text()
