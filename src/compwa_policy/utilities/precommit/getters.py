# noqa: D100
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

from compwa_policy.utilities import CONFIG_PATH

if TYPE_CHECKING:
    from pathlib import Path

    from compwa_policy.utilities.precommit.struct import PrecommitConfig, Repo


def load_precommit_config(path: Path = CONFIG_PATH.precommit) -> PrecommitConfig:
    """Load a **read-only** pre-commit config."""
    with open(path) as stream:
        return yaml.safe_load(stream)


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
