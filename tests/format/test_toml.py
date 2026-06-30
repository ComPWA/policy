import io
import subprocess  # noqa: S404
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.format.toml import (
    _rename_precommit_url,
    _rename_taplo_config,
    _update_precommit_repo,
    _update_taplo_config,
    _update_tomlsort_config,
    _update_tomlsort_hook,
    _update_vscode_extensions,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit

_META_ONLY = dedent("""
    repos:
      - repo: meta
        hooks:
          - id: check-hooks-apply
""").lstrip()

_WITH_MIRRORS_TAPLO = dedent("""
    repos:
      - repo: https://github.com/ComPWA/mirrors-taplo
        rev: v0.8.1
        hooks:
          - id: taplo
""").lstrip()


def _git_init(directory: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=directory, check=True)  # noqa: S607


def describe_rename_precommit_url():
    def migrates_mirror():
        with ModifiablePrecommit.load(io.StringIO(_WITH_MIRRORS_TAPLO)) as precommit:
            _rename_precommit_url(precommit)
        result = precommit.dumps()
        assert any("mirrors-taplo" in m for m in precommit.changelog)
        assert "mirrors-taplo" not in result
        assert "https://github.com/ComPWA/taplo-pre-commit" in result
        assert "rev: v0.8.1" in result  # preserves the pinned revision

    def adds_hook_without_mirror():
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _rename_precommit_url(precommit)
        assert "https://github.com/ComPWA/taplo-pre-commit" in precommit.dumps()


def describe_update_precommit_repo():
    def adds_taplo():
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _update_precommit_repo(precommit)
        result = precommit.dumps()
        assert "https://github.com/ComPWA/taplo-pre-commit" in result
        assert "id: taplo-format" in result

    def migrates_mirror():
        with ModifiablePrecommit.load(io.StringIO(_WITH_MIRRORS_TAPLO)) as precommit:
            _update_precommit_repo(precommit)
        result = precommit.dumps()
        assert "mirrors-taplo" not in result
        assert "https://github.com/ComPWA/taplo-pre-commit" in result


def describe_update_tomlsort_hook():
    def adds_hook_without_excludes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _update_tomlsort_hook(precommit)
        result = precommit.dumps()
        assert "https://github.com/pappasam/toml-sort" in result
        assert "exclude" not in result

    def adds_excludes_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        (tmp_path / "labels.toml").touch()
        monkeypatch.chdir(tmp_path)
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _update_tomlsort_hook(precommit)
        assert "exclude" in precommit.dumps()


def describe_rename_taplo_config():
    def renames_to_dotfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "taplo.toml").write_text("include = []\n")
        changes = _rename_taplo_config()
        assert any("Renamed taplo.toml" in m for m in changes)
        assert not (tmp_path / "taplo.toml").exists()
        assert (tmp_path / ".taplo.toml").exists()


def describe_update_tomlsort_config():
    def configures_sort_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        _update_tomlsort_config()
        result = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.tomlsort]" in result
        assert 'sort_first = ["project"]' in result

    def is_idempotent_without_known_tables(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[tool.other]\nkey = 1\n")
        _update_tomlsort_config()
        assert "sort_first" not in (tmp_path / "pyproject.toml").read_text()
        _update_tomlsort_config()  # second run is a no-op


def describe_update_taplo_config():
    def creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        changes = _update_taplo_config()
        assert any(".taplo.toml" in m for m in changes)
        assert (tmp_path / ".taplo.toml").exists()


def describe_update_vscode_extensions():
    def recommends_even_better_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # cspell:ignore tamasfe
        monkeypatch.chdir(tmp_path)
        changes = _update_vscode_extensions()
        assert changes
        extensions = (tmp_path / ".vscode" / "extensions.json").read_text()
        assert "tamasfe.even-better-toml" in extensions


def describe_main():
    def runs_when_triggered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            changes = main(precommit)
        result = precommit.dumps()
        assert changes or precommit.changelog
        assert "https://github.com/ComPWA/taplo-pre-commit" in result
        assert "https://github.com/pappasam/toml-sort" in result

    def skips_without_trigger_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            main(precommit)  # no pyproject.toml or taplo config -> no-op
