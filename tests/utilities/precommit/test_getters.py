import io
from pathlib import Path

import pytest

from compwa_policy.utilities.precommit import Precommit, getters
from compwa_policy.utilities.precommit.getters import find_repo, find_repo_with_index


@pytest.fixture(scope="session")
def example_yaml() -> str:
    config_path = Path(__file__).parent / ".pre-commit-config.yaml"
    with open(config_path) as stream:
        return stream.read()


@pytest.fixture(autouse=True)  # noqa: RUF076
def _offline_git_ls_remote() -> None:
    """Override the global offline patch so the real implementation is exercised."""


@pytest.mark.parametrize("use_stream", [True, False])
def test_load_precommit_config(example_yaml: str, use_stream: bool):
    if use_stream:
        stream = io.StringIO(example_yaml)
        config = Precommit.load(stream).document
    else:
        config = Precommit.load(example_yaml).document
    assert set(config) == {"ci", "repos"}

    ci = config.get("ci")
    assert ci is not None
    assert ci.get("autoupdate_schedule") == "quarterly"

    repos = config.get("repos")
    assert repos is not None
    assert len(repos) == 3


def test_load_precommit_config_path():
    config = Precommit.load().document
    assert "ci" in config
    ci = config.get("ci")
    assert ci is not None
    assert ci.get("autoupdate_commit_msg") == "MAINT: upgrade lock files"


def test_find_repo(example_yaml: str):
    config = Precommit.load(example_yaml).document
    repo = find_repo(config, "ComPWA/policy")
    assert repo is not None
    assert repo["repo"] == "https://github.com/ComPWA/policy"
    assert repo["rev"] == "0.3.0"
    assert len(repo["hooks"]) == 1


def test_find_repo_with_index(example_yaml: str):
    config = Precommit.load(example_yaml).document

    repo_and_idx = find_repo_with_index(config, "ComPWA/policy")
    assert repo_and_idx is not None
    index, repo = repo_and_idx
    assert index == 1
    assert repo["repo"] == "https://github.com/ComPWA/policy"

    assert find_repo_with_index(config, "non-existent") is None


class TestGetLatestRev:
    def test_returns_the_highest_tag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ls_remote = (
            "sha1\trefs/tags/0.0.1\nsha2\trefs/tags/0.0.10\nsha3\trefs/tags/0.0.2\n"
        )
        monkeypatch.setattr(getters, "_git_ls_remote_tags", lambda _url: ls_remote)
        assert getters.get_latest_rev("https://example.test/repo") == "0.0.10"

    def test_ignores_non_version_tags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ls_remote = "sha1\trefs/tags/nightly\nsha2\trefs/tags/1.2.3\n"
        monkeypatch.setattr(getters, "_git_ls_remote_tags", lambda _url: ls_remote)
        assert getters.get_latest_rev("https://example.test/repo") == "1.2.3"

    def test_falls_back_without_tags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(getters, "_git_ls_remote_tags", lambda _url: "")
        assert getters.get_latest_rev("https://example.test/repo") == "PLEASE-UPDATE"
        assert getters.get_latest_rev("https://x", fallback="1.0.0") == "1.0.0"

    def test_git_ls_remote_tags_returns_empty_when_offline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_a: object, **_k: object) -> str:
            msg = "no network"
            raise OSError(msg)

        monkeypatch.setattr(getters.subprocess, "check_output", _raise)
        assert not getters._git_ls_remote_tags("https://example.test/repo")
