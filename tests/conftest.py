import os
import subprocess  # noqa: S404
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from compwa_policy import _characterization
from compwa_policy.cli._options import build_arguments
from compwa_policy.repo import readthedocs
from compwa_policy.utilities import match
from compwa_policy.utilities.check_hook import CheckContext, CheckHook
from compwa_policy.utilities.precommit import getters
from compwa_policy.utilities.session import Session

GitCommand = Callable[[Path], None]


@pytest.fixture
def run_check() -> Callable[..., None]:
    def run(
        check: CheckHook,
        session: Session,
        *,
        is_python_repo: bool = True,
        has_notebooks: bool = False,
        doc_apt_packages: list[str] | None = None,
        environment_variables: dict[str, str] | None = None,
        **argument_overrides: Any,
    ) -> None:
        argument_overrides.setdefault("dev_python_version", "3.12")
        args = build_arguments(**argument_overrides)
        context = CheckContext(
            is_python_repo=is_python_repo,
            has_notebooks=has_notebooks,
            doc_apt_packages=doc_apt_packages or [],
            environment_variables=environment_variables or {},
        )
        check(session, args, context)

    return run


@pytest.fixture(scope="session")
def test_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture
def git_init() -> GitCommand:
    def run(directory: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=directory, check=True)  # noqa: S607

    return run


@pytest.fixture
def git_add() -> GitCommand:
    def run(directory: Path) -> None:
        subprocess.run(["git", "add", "-A"], cwd=directory, check=True)  # noqa: S607

    return run


@pytest.fixture
def git_commit(git_init: GitCommand, git_add: GitCommand) -> GitCommand:
    """Initialize a repository in a directory, stage everything, and commit it."""

    def run(directory: Path) -> None:
        git_init(directory)
        git_add(directory)
        subprocess.run(
            ["git", "commit", "-qm", "init", "--allow-empty"],  # noqa: S607
            cwd=directory,
            check=True,
        )

    return run


@pytest.fixture(scope="session")
def _hermetic_gitconfig(tmp_path_factory: pytest.TempPathFactory) -> Path:
    config = tmp_path_factory.mktemp("gitconfig") / "config"
    config.write_text(
        "[user]\n"
        "\tname = ComPWA\n"
        "\temail = compwa@example.com\n"
        "[init]\n"
        "\tdefaultBranch = main\n"
    )
    return config


@pytest.fixture(autouse=True)
def _hermetic_git(monkeypatch: pytest.MonkeyPatch, _hermetic_gitconfig: Path) -> None:
    """Isolate git in tests from the developer's global and system configuration.

    Tests create throwaway repositories in ``tmp_path`` and commit into them. If those
    commits inherit the developer's global config with commit signing enabled, every
    commit shells out to a gpg-agent, which under a burst of commits across the suite
    fails intermittently with ``fatal: failed to write commit object``. Pointing git at
    a dedicated config (which leaves signing at its ``false`` default) and supplying a
    fixed identity makes the commits hermetic and deterministic.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(_hermetic_gitconfig))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "ComPWA")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "compwa@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "ComPWA")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "compwa@example.com")


@pytest.fixture(autouse=True)
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


@pytest.fixture(autouse=True)
def _offline_git_ls_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test suite offline: pretend ``git ls-remote`` finds no tags.

    As a result, `.get_latest_rev` returns its fallback, which keeps the pinned
    revisions in golden ``.pre-commit-config.yaml`` files deterministic. Override this
    fixture (see ``tests/utilities/precommit/test_getters.py``) to exercise the real
    implementation.
    """
    monkeypatch.setattr(getters, "_git_ls_remote_tags", lambda _repo_url: "")
