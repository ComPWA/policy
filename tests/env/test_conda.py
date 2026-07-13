from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.env import conda
from compwa_policy.utilities.session import Session

_ENVIRONMENT = dedent("""
    name: my-package
    channels:
      - defaults
    dependencies:
      - python==3.10.*
      - pip
      - pip:
          - -e .[dev]
""").lstrip()


def _write_pyproject(directory: Path) -> None:
    (directory / "pyproject.toml").write_text('[project]\nname = "my-package"\n')


def describe_main():
    def creates_environment_for_conda(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path)
        with Session() as session:
            conda.main(session, "3.12", "conda")
        result = (tmp_path / "environment.yml").read_text()
        assert "python==3.12.*" in result

    def removes_environment_for_other_manager(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT)
        with Session() as session:
            conda.main(session, "3.12", "uv")
        assert not (tmp_path / "environment.yml").exists()


def describe_update_conda_environment():
    def is_noop_without_package_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nversion = '0.1'\n")
        with Session() as session:
            conda.update_conda_environment("3.12", session=session)

    def updates_python_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path)
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT)
        with Session() as session:
            changes = conda.update_conda_environment("3.12", session=session)
        assert any("Updated Conda environment" in m for m in changes)
        result = (tmp_path / "environment.yml").read_text()
        assert "python==3.12.*" in result

    def is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path)
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT.replace("3.10", "3.12"))
        with Session() as session:
            conda.update_conda_environment("3.12", session=session)

    def uses_constraints_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path)
        constraints = tmp_path / ".constraints"
        constraints.mkdir()
        (constraints / "py3.12.txt").write_text("numpy==1.0\n")
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT.replace("3.10", "3.12"))
        with Session() as session:
            changes = conda.update_conda_environment("3.12", session=session)
        assert any("Updated Conda environment" in m for m in changes)
        result = (tmp_path / "environment.yml").read_text()
        assert "-c .constraints/py3.12.txt -e .[dev]" in result
