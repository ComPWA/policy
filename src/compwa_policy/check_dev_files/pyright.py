"""Check and update :code:`mypy` settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    complies_with_subset,
)
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit


def main(precommit: ModifiablePrecommit) -> None:
    with ModifiablePyproject.load() as pyproject:
        _merge_config_into_pyproject(pyproject)
        _update_precommit(precommit, pyproject)
        _update_settings(pyproject)


def _merge_config_into_pyproject(
    pyproject: ModifiablePyproject,
    path: Path = Path("pyrightconfig.json"),
    remove: bool = True,
) -> None:
    old_config_path = path
    if not os.path.exists(old_config_path):
        return
    with open(old_config_path) as stream:
        existing_config = json.load(stream)
    for key, value in existing_config.items():
        if isinstance(value, list):
            existing_config[key] = to_toml_array(sorted(value))
    tool_table = pyproject.get_table("tool.pyright", create=True)
    tool_table.update(existing_config)
    if remove:
        os.remove(old_config_path)
    msg = f"Imported pyright configuration from {old_config_path}"
    pyproject.changelog.append(msg)


def _update_precommit(precommit: ModifiablePrecommit, pyproject: Pyproject) -> None:
    if not __has_pyright(pyproject):
        return
    old_url = "https://github.com/ComPWA/mirrors-pyright"
    old_repo = precommit.find_repo(old_url)
    rev = ""
    if old_repo is not None:
        precommit.remove_hook("pyright", old_url)
        rev = old_repo["rev"]
    repo = Repo(
        repo="https://github.com/ComPWA/pyright-pre-commit",
        rev=rev,
        hooks=[Hook(id="pyright")],
    )
    precommit.update_single_hook_repo(repo)


def _update_settings(pyproject: ModifiablePyproject) -> None:
    if not __has_pyright(pyproject):
        return
    pyright_settings = pyproject.get_table("tool.pyright")
    minimal_settings = {
        "typeCheckingMode": "strict",
    }
    if not complies_with_subset(pyright_settings, minimal_settings):
        pyright_settings.update(minimal_settings)
        msg = "Updated pyright configuration"
        pyproject.changelog.append(msg)


def __has_pyright(pyproject: Pyproject) -> bool:
    table_key = "tool.pyright"
    return pyproject.has_table(table_key)
