import io
import json
import subprocess  # noqa: S404
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
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


def _git_init(directory: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=directory, check=True)  # noqa: S607


def describe_update_cspell_repo_url():
    def migrates_mirror_url():
        bad_config = dedent("""
            repos:
              - repo: https://github.com/ComPWA/mirrors-cspell
                rev: v5.10.1
                hooks:
                  - id: cspell
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Updated cSpell pre-commit repo URL"),
            ModifiablePrecommit.load(io.StringIO(bad_config)) as precommit,
        ):
            _update_cspell_repo_url(precommit)

        repo_url = precommit.document["repos"][0]["repo"]
        assert repo_url == "https://github.com/streetsidesoftware/cspell-cli"


def describe_remove_configuration():
    def removes_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text("{}")
        with pytest.raises(PrecommitError, match=r"no longer required"):
            _remove_configuration()
        assert not (tmp_path / ".cspell.json").exists()

    def cleans_editorconfig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".editorconfig").write_text(".cspell.json\nother-entry\n")
        with pytest.raises(PrecommitError, match=r"no longer"):
            _remove_configuration()
        assert ".cspell.json" not in (tmp_path / ".editorconfig").read_text()


def describe_update_precommit_repo():
    def adds_cspell_hook():
        config = dedent("""
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(config)) as precommit,
        ):
            _update_precommit_repo(precommit)
        result = precommit.dumps()
        assert "https://github.com/streetsidesoftware/cspell-cli" in result
        assert "id: cspell" in result


def describe_update_config_content():
    def fixes_wrong_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        template = json.loads(
            (COMPWA_POLICY_DIR / ".template" / CONFIG_PATH.cspell).read_text()
        )
        template["language"] = "xx-XX"
        (tmp_path / ".cspell.json").write_text(json.dumps(template))
        with pytest.raises(PrecommitError, match=r"has been updated"):
            _update_config_content()
        config = json.loads((tmp_path / ".cspell.json").read_text())
        assert config["language"] == "en-US"

    def populates_empty_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text("{}")
        with pytest.raises(PrecommitError, match=r"has been updated"):
            _update_config_content()
        config = json.loads((tmp_path / ".cspell.json").read_text())
        assert config["language"] == "en-US"


def describe_sort_config_entries():
    def sorts_words_alphabetically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text(
            json.dumps({"words": ["zebra", "apple", "mango"]})
        )
        with pytest.raises(PrecommitError, match=r"sorted alphabetically"):
            _sort_config_entries()
        config = json.loads((tmp_path / ".cspell.json").read_text())
        assert config["words"] == ["apple", "mango", "zebra"]


def describe_main():
    def updates_existing_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / ".cspell.json").write_text('{"words": ["zebra", "apple"]}')
        config = dedent("""
            repos:
              - repo: https://github.com/streetsidesoftware/cspell-cli
                rev: v8.0.0
                hooks:
                  - id: cspell
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(config)) as precommit,
        ):
            main(precommit, no_cspell_update=True)
        result = json.loads((tmp_path / ".cspell.json").read_text())
        assert result["words"] == ["apple", "zebra"]  # sorted

    def removes_config_without_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cspell.json").write_text("{}")
        with (
            ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit,
            pytest.raises(PrecommitError, match=r"no longer required"),
        ):
            main(precommit, no_cspell_update=False)
        assert not (tmp_path / ".cspell.json").exists()
