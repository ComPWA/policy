# noqa: D100
from __future__ import annotations

import operator
import re
import subprocess  # noqa: S404
from typing import TYPE_CHECKING

from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit.struct import Hook, PrecommitConfig, Repo


def find_hook(config: PrecommitConfig, search_pattern: str) -> Hook | None:
    """Find pre-commit hook definition in pre-commit config."""
    repos = config.get("repos", [])
    for repo in repos:
        hooks = repo.get("hooks", [])
        for hook in hooks:
            if re.search(search_pattern, hook.get("id", "")):
                return hook
    return None


def find_repo(config: PrecommitConfig, search_pattern: str) -> Repo | None:
    """Find pre-commit repo definition in pre-commit config."""
    repos = config.get("repos", [])
    for repo in repos:
        url = repo.get("repo", "")
        if re.search(search_pattern, url):
            return repo
    return None


def find_repo_with_index(
    config: PrecommitConfig, search_pattern: str
) -> tuple[int, Repo] | None:
    """Find pre-commit repo definition and its index in pre-commit config."""
    repos = config.get("repos", [])
    for i, repo in enumerate(repos):
        url = repo.get("repo", "")
        if re.search(search_pattern, url):
            return i, repo
    return None


def get_latest_rev(repo_url: str, fallback: str = "PLEASE-UPDATE") -> str:
    """Fetch the latest release tag of a pre-commit hook repository.

    Returns the highest version tag found through ``git ls-remote``, or :code:`fallback`
    when the tags cannot be fetched (for example when there is no internet connection).
    """
    versions: list[tuple[Version, str]] = []
    for line in _git_ls_remote_tags(repo_url).splitlines():
        _, _, tag = line.partition("refs/tags/")
        if not tag:
            continue
        try:
            versions.append((Version(tag), tag))
        except InvalidVersion:
            continue
    if not versions:
        return fallback
    return max(versions, key=operator.itemgetter(0))[1]


def _git_ls_remote_tags(repo_url: str) -> str:
    try:
        return subprocess.check_output(  # noqa: S603
            ["git", "ls-remote", "--tags", "--refs", repo_url],  # noqa: S607
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
