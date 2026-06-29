from pathlib import Path

import pytest

from compwa_policy import _characterization
from compwa_policy.repo import readthedocs
from compwa_policy.utilities import match
from compwa_policy.utilities.precommit import getters


@pytest.fixture(scope="session")
def test_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture(autouse=True)  # noqa: RUF076
def _clear_git_ls_files_cache() -> None:
    """Reset caches that depend on the working directory but do not key on it.

    ``git ls-files`` and the repository characterization helpers are cached, so a test
    that builds a repository in a ``tmp_path`` would otherwise see a stale result cached
    by an earlier test running in a different working directory.
    """
    match._git_ls_files_cmd.cache_clear()
    _characterization.has_documentation.cache_clear()
    _characterization.has_python_code.cache_clear()
    readthedocs._determine_docs_dir.cache_clear()


@pytest.fixture(autouse=True)  # noqa: RUF076
def _offline_git_ls_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test suite offline: pretend ``git ls-remote`` finds no tags.

    As a result, `.get_latest_rev` returns its fallback, which keeps the pinned
    revisions in golden ``.pre-commit-config.yaml`` files deterministic. Override this
    fixture (see ``tests/utilities/precommit/test_getters.py``) to exercise the real
    implementation.
    """
    monkeypatch.setattr(getters, "_git_ls_remote_tags", lambda _repo_url: "")
