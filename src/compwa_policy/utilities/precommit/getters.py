# noqa: D100
from __future__ import annotations

import re
from typing import TYPE_CHECKING

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
