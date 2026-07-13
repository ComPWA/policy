import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.format.cspell import (
    _remove_configuration,
    _sort_config_entries,
    _update_config_content,
    _update_cspell_repo_url,
    _update_precommit_repo,
    main,
)
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session


def _write_precommit(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".pre-commit-config.yaml"
    path.write_text(dedent(content).lstrip())
    return path


def describe_update_cspell_repo_url():
    def migrates_mirror_url(tmp_path: Path):
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: https://github.com/ComPWA/mirrors-cspell
                rev: v5.10.1
                hooks:
                  - id: cspell
            """,
        )
        with ModifiablePrecommit.load(config) as precommit:
            _update_cspell_repo_url(precommit)
        assert any(
            "Updated cSpell pre-commit repo URL" in m for m in precommit.changelog
        )
        repo_url = precommit.document["repos"][0]["repo"]
        assert repo_url == "https://github.com/streetsidesoftware/cspell-cli"


def describe_remove_configuration():
    def removes_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text("{}")
        with Session() as session:
            _remove_configuration(session)
            changes = session.collect_changes()
        assert any("no longer required" in m for m in changes)
        assert not (tmp_path / ".cspell.json").exists()

    def cleans_editorconfig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".editorconfig").write_text(".cspell.json\nother-entry\n")
        with Session() as session:
            _remove_configuration(session)
            changes = session.collect_changes()
        assert any("no longer" in m for m in changes)
        assert ".cspell.json" not in (tmp_path / ".editorconfig").read_text()


def describe_update_precommit_repo():
    def adds_cspell_hook(tmp_path: Path):
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
            """,
        )
        with ModifiablePrecommit.load(config) as precommit:
            _update_precommit_repo(precommit)
        assert precommit.changelog  # something was changed
        result = precommit.dumps()
        assert "https://github.com/streetsidesoftware/cspell-cli" in result
        assert "id: cspell" in result


def describe_update_config_content():
    def fixes_wrong_value(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        template = json.loads(
            (COMPWA_POLICY_DIR / ".template" / CONFIG_PATH.cspell).read_text()
        )
        template["language"] = "xx-XX"
        (tmp_path / ".cspell.json").write_text(json.dumps(template))
        changes = _update_config_content()
        assert any("has been updated" in m for m in changes)
        config = json.loads((tmp_path / ".cspell.json").read_text())
        assert config["language"] == "en-US"

    def populates_empty_config(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text("{}")
        changes = _update_config_content()
        assert any("has been updated" in m for m in changes)
        config = json.loads((tmp_path / ".cspell.json").read_text())
        assert config["language"] == "en-US"


def describe_sort_config_entries():
    def sorts_words_alphabetically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text(
            json.dumps({"words": ["zebra", "apple", "mango"]})
        )
        changes = _sort_config_entries()
        assert any("sorted alphabetically" in m for m in changes)
        config = json.loads((tmp_path / ".cspell.json").read_text())
        assert config["words"] == ["apple", "mango", "zebra"]


def describe_main():
    def updates_existing_config(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / ".cspell.json").write_text('{"words": ["zebra", "apple"]}')
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: https://github.com/streetsidesoftware/cspell-cli
                rev: v8.0.0
                hooks:
                  - id: cspell
            """,
        )
        precommit = ModifiablePrecommit.load(config)
        with Session.load(precommit) as session:
            main(session, no_cspell_update=True)
            changes = session.collect_changes()
        assert changes or precommit.changelog  # something changed
        result = json.loads((tmp_path / ".cspell.json").read_text())
        assert result["words"] == ["apple", "zebra"]

    def removes_config_without_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text("{}")
        config = _write_precommit(tmp_path, "repos: []\n")
        precommit = ModifiablePrecommit.load(config)
        with Session.load(precommit) as session:
            main(session, no_cspell_update=False)
            changes = session.collect_changes()
        assert any("no longer required" in m for m in changes)
        assert not (tmp_path / ".cspell.json").exists()
