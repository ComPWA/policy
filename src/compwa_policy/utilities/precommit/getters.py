# noqa: D100
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import IO, TYPE_CHECKING

import yaml

from compwa_policy.utilities import CONFIG_PATH

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit.struct import PrecommitConfig, Repo


def load_precommit_config(
    source: IO | Path | str = CONFIG_PATH.precommit,
) -> PrecommitConfig:
    """Load a **read-only** pre-commit config."""
    if isinstance(source, io.IOBase):
        current_position = source.tell()
        source.seek(0)
        document = yaml.safe_load(source)
        source.seek(current_position)
        return document
    if isinstance(source, Path):
        with open(source) as stream:
            return yaml.safe_load(stream)
    if isinstance(source, str):
        stream = io.StringIO(source)
        return load_precommit_config(stream)
    msg = f"Source of type {type(source).__name__} is not supported"
    raise TypeError(msg)


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
