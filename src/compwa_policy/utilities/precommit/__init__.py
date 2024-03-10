"""Helper functions for modifying :file:`.pre-commit.config.yaml`."""

from __future__ import annotations

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

__all__ = [
    "Hook",
    "PrecommitConfig",
    "Repo",
    "find_repo",
    "find_repo_with_index",
    "load_precommit_config",
    "load_roundtrip_precommit_config",
    "remove_precommit_hook",
    "update_precommit_hook",
    "update_single_hook_precommit_repo",
]
