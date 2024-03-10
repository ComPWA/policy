"""Helper functions for modifying :file:`.pre-commit.config.yaml`."""

from __future__ import annotations

from typing import IO, TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit.getters import (
    find_repo,
    find_repo_with_index,
    load_precommit_config,
)
from compwa_policy.utilities.precommit.setters import (
    load_roundtrip_precommit_config,
    remove_precommit_hook,
    update_precommit_hook,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.precommit.struct import Hook, PrecommitConfig, Repo

if TYPE_CHECKING:
    from pathlib import Path


__all__ = [
    "Hook",
    "Precommit",
    "PrecommitConfig",
    "Repo",
    "load_roundtrip_precommit_config",
    "remove_precommit_hook",
    "update_precommit_hook",
    "update_single_hook_precommit_repo",
]


class Precommit:
    """Read-only representation of a :code:`.pre-commit-config.yaml` file."""

    def __init__(self, document: PrecommitConfig) -> None:
        self.__document = document

    @property
    def document(self) -> PrecommitConfig:
        return self.__document

    @classmethod
    def load(cls, source: IO | Path | str = CONFIG_PATH.precommit) -> Precommit:
        """Load a :code:`pyproject.toml` file from a file, I/O stream, or `str`."""
        config = load_precommit_config(source)
        return cls(config)

    def find_repo(self, search_pattern: str) -> Repo | None:
        """Find pre-commit repo definition in pre-commit config."""
        return find_repo(self.__document, search_pattern)

    def find_repo_with_index(self, search_pattern: str) -> tuple[int, Repo] | None:
        """Find pre-commit repo definition and its index in pre-commit config."""
        return find_repo_with_index(self.__document, search_pattern)
