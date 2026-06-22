from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.env import conda
from compwa_policy.errors import PrecommitError

# cspell:ignore condaenv pyproject

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
        with pytest.raises(PrecommitError, match=r"Updated Conda environment"):
            conda.main("3.12", "conda")
        result = (tmp_path / "environment.yml").read_text()
        assert "python==3.12.*" in result

    def removes_environment_for_other_manager(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT)
        with pytest.raises(PrecommitError, match=r"Removed Conda configuration"):
            conda.main("3.12", "uv")
        assert not (tmp_path / "environment.yml").exists()


def describe_update_conda_environment():
    def is_noop_without_package_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nversion = '0.1'\n")
        conda.update_conda_environment("3.12")  # no package name -> no-op

    def updates_python_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path)
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT)
        with pytest.raises(PrecommitError, match=r"Updated Conda environment"):
            conda.update_conda_environment("3.12")
        result = (tmp_path / "environment.yml").read_text()
        assert "python==3.12.*" in result

    def is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path)
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT.replace("3.10", "3.12"))
        conda.update_conda_environment("3.12")  # already up to date -> no error

    def uses_constraints_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path)
        constraints = tmp_path / ".constraints"
        constraints.mkdir()
        (constraints / "py3.12.txt").write_text("numpy==1.0\n")
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT.replace("3.10", "3.12"))
        with pytest.raises(PrecommitError, match=r"Updated Conda environment"):
            conda.update_conda_environment("3.12")
        result = (tmp_path / "environment.yml").read_text()
        assert "-c .constraints/py3.12.txt -e .[dev]" in result
