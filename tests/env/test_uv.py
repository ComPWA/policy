import io
import subprocess  # noqa: S404
from pathlib import Path

import pytest

from compwa_policy.env.uv import (
    _remove_pip_constraint_files,
    _remove_uv_configuration,
    _remove_uv_lock,
    _update_contributing_file,
    _update_editor_config,
    _update_python_version_file,
    _update_uv_lock_hook,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit


def _git_init(directory: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=directory, check=True)  # noqa: S607


def _git_add(directory: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=directory, check=True)  # noqa: S607


def describe_remove_uv_lock():
    def removes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").write_text("# lock\n")
        changes = _remove_uv_lock()
        assert any("Removed uv.lock" in m for m in changes)
        assert not (tmp_path / "uv.lock").exists()


def describe_remove_uv_configuration():
    def removes_tool_uv_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\n\n[tool.uv]\nmanaged = true\n'
        )
        _remove_uv_configuration()
        assert "[tool.uv]" not in (tmp_path / "pyproject.toml").read_text()


def describe_remove_pip_constraint_files():
    def removes_constraints_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        constraints = tmp_path / ".constraints"
        constraints.mkdir()
        (constraints / "py3.10.txt").write_text("numpy==1.0\n")
        changes = _remove_pip_constraint_files()
        assert any("Removed deprecated" in m for m in changes)
        assert not constraints.exists()


def describe_update_uv_lock_hook():
    def adds_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        (tmp_path / "uv.lock").write_text("# lock\n")
        _git_add(tmp_path)
        monkeypatch.chdir(tmp_path)
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit:
            _update_uv_lock_hook(precommit)
        assert precommit.changelog  # something changed
        assert "uv-lock" in precommit.dumps()

    def removes_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        config = (
            "repos:\n"
            "  - repo: https://github.com/astral-sh/uv-pre-commit\n"
            "    rev: 0.4.20\n"
            "    hooks:\n"
            "      - id: uv-lock\n"
        )
        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            _update_uv_lock_hook(precommit)
        assert precommit.changelog  # something changed
        assert "uv-lock" not in precommit.dumps()


def describe_update_python_version_file():
    def writes_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.10"\n'
        )
        changes = _update_python_version_file("3.12")
        assert any("Updated .python-version" in m for m in changes)
        assert (tmp_path / ".python-version").read_text().strip() == "3.12"

    def removes_file_when_pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = "==3.12.*"\n'
        )
        (tmp_path / ".python-version").write_text("3.12\n")
        changes = _update_python_version_file("3.12")
        assert any("Removed .python-version" in m for m in changes)
        assert not (tmp_path / ".python-version").exists()

    def is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.10"\n'
        )
        (tmp_path / ".python-version").write_text("3.12\n")
        _update_python_version_file("3.12")  # already up to date -> no error


def describe_update_editor_config():
    def appends_uv_lock_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        (tmp_path / "uv.lock").write_text("# lock\n")
        (tmp_path / ".editorconfig").write_text("root = true\n")
        _git_add(tmp_path)
        monkeypatch.chdir(tmp_path)
        _update_editor_config()  # appends a [uv.lock] section, no error
        assert "[uv.lock]" in (tmp_path / ".editorconfig").read_text()


def describe_update_contributing_file():
    def selects_poe_instructions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poe.tasks.style]\ncmd = "check"\n'
        )
        (tmp_path / "CONTRIBUTING.md").write_text("outdated\n")
        changes = _update_contributing_file("ComPWA", "policy")
        assert any("Updated CONTRIBUTING.md" in m for m in changes)
        result = (tmp_path / "CONTRIBUTING.md").read_text()
        assert "policy" in result
        assert "Poe the Poet" in result  # runner instructions from tool.poe.tasks


def describe_main():
    def configures_uv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.10"\n'
        )
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit:
            changes = main(
                precommit,
                dev_python_version="3.12",
                keep_contributing_md=True,
                package_manager="uv",
                organization="ComPWA",
                repo_name="policy",
            )
        assert changes or precommit.changelog  # something changed
        assert (tmp_path / ".python-version").read_text().strip() == "3.12"

    def removes_uv_for_other_package_manager(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\n\n[tool.uv]\nmanaged = true\n'
        )
        (tmp_path / "uv.lock").write_text("# lock\n")
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit:
            main(
                precommit,
                dev_python_version="3.12",
                keep_contributing_md=True,
                package_manager="pixi",
                organization="ComPWA",
                repo_name="policy",
            )
        assert not (tmp_path / "uv.lock").exists()
        assert "[tool.uv]" not in (tmp_path / "pyproject.toml").read_text()
