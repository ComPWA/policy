import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.format.prettier import (
    _remove_configuration,
    _update_prettier_hook,
    _update_prettier_ignore,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session

_META_ONLY = dedent("""
    repos:
      - repo: meta
        hooks:
          - id: check-hooks-apply
""").lstrip()

_WITH_MIRROR = dedent("""
    repos:
      - repo: https://github.com/prettier/mirrors-prettier
        rev: v3.1.0
        hooks:
          - id: prettier
""").lstrip()

_WITH_PRETTIER = dedent("""
    repos:
      - repo: https://github.com/ComPWA/prettier-pre-commit
        rev: v3.4.2
        hooks:
          - id: prettier
""").lstrip()


def describe_update_prettier_hook():
    def renames_mirror():
        with ModifiablePrecommit.load(io.StringIO(_WITH_MIRROR)) as precommit:
            _update_prettier_hook(precommit)
        assert "https://github.com/ComPWA/prettier-pre-commit" in precommit.dumps()

    def is_noop_without_mirror():
        with ModifiablePrecommit.load(io.StringIO(_WITH_PRETTIER)) as precommit:
            _update_prettier_hook(precommit)  # already migrated -> no change


def describe_remove_configuration():
    def removes_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".prettierrc.json").write_text("{}")
        (tmp_path / ".prettierrc").write_text("{}")
        changes = _remove_configuration()
        assert any("Removed redundant configuration files" in m for m in changes)
        assert not (tmp_path / ".prettierrc.json").exists()
        assert not (tmp_path / ".prettierrc").exists()

    def is_noop_without_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        _remove_configuration()  # no config files and no badge to remove


def describe_update_prettier_ignore():
    def removes_forbidden_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".prettierignore").write_text(".cspell.json\nbuild/\n")
        changes = _update_prettier_ignore()
        assert any("Removed forbidden paths" in m for m in changes)
        assert ".cspell.json" not in (tmp_path / ".prettierignore").read_text()

    def inserts_obligatory_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "LICENSE").touch()
        (tmp_path / ".prettierignore").write_text("build/\n")
        changes = _update_prettier_ignore()
        assert any("Added paths" in m for m in changes)
        assert "LICENSE" in (tmp_path / ".prettierignore").read_text()

    def ignores_generated_lock_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pixi.lock").touch()
        (tmp_path / "uv.lock").touch()  # Prettier ignores TOML lock files
        changes = _update_prettier_ignore()
        assert any("Added paths" in m for m in changes)
        prettier_ignore = (tmp_path / ".prettierignore").read_text()
        assert "pixi.lock" in prettier_ignore
        assert "uv.lock" not in prettier_ignore

    def removes_empty_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".prettierignore").write_text("")
        changes = _update_prettier_ignore()
        assert any("is not needed" in m for m in changes)
        assert not (tmp_path / ".prettierignore").exists()


def describe_main():
    def updates_readme_with_prettier_repo(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        precommit = ModifiablePrecommit.load(io.StringIO(_WITH_PRETTIER))
        with Session.load(precommit) as session:
            main(session)
            changes = session.collect_changes()
        assert changes
        assert "prettier" in (tmp_path / "README.md").read_text()

    def cleans_up_without_prettier_repo(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / ".prettierrc.json").write_text("{}")
        precommit = ModifiablePrecommit.load(io.StringIO(_META_ONLY))
        with Session.load(precommit) as session:
            main(session)
            changes = session.collect_changes()
        assert any("Removed redundant configuration" in m for m in changes)
