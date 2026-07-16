from pathlib import Path

import pytest

from compwa_policy.nb import jupyter
from compwa_policy.utilities.session import Session


def describe_check() -> None:
    def excludes_configured_dependencies(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run_check,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            """
[project]
name = "x"
requires-python = ">=3.12"

[dependency-groups]
jupyter = ["python-lsp-server"]
dev = [
    { include-group = "jupyter" },
]
""".lstrip()
        )

        with Session() as session:
            run_check(
                jupyter.check,
                session,
                has_notebooks=True,
                excluded_dependencies=["python_lsp_server"],
            )

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert "python-lsp-server" not in pyproject
        assert "jupyterlab-lsp" in pyproject

    def adds_default_dependencies_without_exclusions(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run_check,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.12"\n'
        )

        with Session() as session:
            run_check(jupyter.check, session, has_notebooks=True)

        assert "python-lsp-server" in (tmp_path / "pyproject.toml").read_text()
