"""Check and update :code:`mypy` settings."""

from __future__ import annotations

import json
import os
from pathlib import Path

from compwa_policy.utilities.pyproject import ModifiablePyproject, complies_with_subset
from compwa_policy.utilities.toml import to_toml_array


def main() -> None:
    with ModifiablePyproject.load() as pyproject:
        _merge_config_into_pyproject(pyproject)
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
    pyproject.append_to_changelog(msg)


def _update_settings(pyproject: ModifiablePyproject) -> None:
    table_key = "tool.pyright"
    if not pyproject.has_table(table_key):
        return
    pyright_settings = pyproject.get_table("tool.pyright")
    minimal_settings = {
        "typeCheckingMode": "strict",
    }
    if not complies_with_subset(pyright_settings, minimal_settings):
        pyright_settings.update(minimal_settings)
        msg = "Updated pyright configuration"
        pyproject.append_to_changelog(msg)
