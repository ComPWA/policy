"""Check and update :code:`mypy` settings."""

from __future__ import annotations

import json
import os

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject, complies_with_subset
from compwa_policy.utilities.toml import to_toml_array


def main() -> None:
    with Pyproject.load() as pyproject:
        _merge_config_into_pyproject(pyproject)
        _update_settings(pyproject)


def _merge_config_into_pyproject(pyproject: Pyproject) -> None:
    config_path = "pyrightconfig.json"  # cspell:ignore pyrightconfig
    if not os.path.exists(config_path):
        return
    with open(config_path) as stream:
        existing_config = json.load(stream)
    for key, value in existing_config.items():
        if isinstance(value, list):
            existing_config[key] = to_toml_array(sorted(value))
    tool_table = pyproject.get_table("tool.pyright", create=True)
    tool_table.update(existing_config)
    os.remove(config_path)
    msg = f"Moved pyright configuration to {CONFIG_PATH.pyproject}"
    pyproject.modifications.append(msg)


def _update_settings(pyproject: Pyproject) -> None:
    table_key = "tool.pyright"
    if not pyproject.has_table(table_key):
        return
    pyright_settings = pyproject.get_table("tool.pyright")
    minimal_settings = {
        "typeCheckingMode": "strict",
    }
    if not complies_with_subset(pyright_settings, minimal_settings):
        pyright_settings.update(minimal_settings)
        msg = f"Updated pyright configuration in {CONFIG_PATH.pyproject}"
        pyproject.modifications.append(msg)
