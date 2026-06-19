from pathlib import Path

import pytest

from compwa_policy.utilities.precommit import getters


@pytest.fixture(scope="session")
def test_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture(autouse=True)  # noqa: RUF076
def _offline_git_ls_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test suite offline: pretend ``git ls-remote`` finds no tags.

    As a result, `.get_latest_rev` returns its fallback, which keeps the pinned
    revisions in golden ``.pre-commit-config.yaml`` files deterministic. Override this
    fixture (see ``tests/utilities/precommit/test_getters.py``) to exercise the real
    implementation.
    """
    monkeypatch.setattr(getters, "_git_ls_remote_tags", lambda _repo_url: "")
