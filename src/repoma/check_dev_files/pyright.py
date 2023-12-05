"""Check and update :code:`mypy` settings."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.pyproject import (
    complies_with_subset,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)

if TYPE_CHECKING:
    from tomlkit.items import Table


def main() -> None:
    executor = Executor()
    executor(_merge_config_into_pyproject)
    executor(_update_settings)
    executor.finalize()


def _merge_config_into_pyproject() -> None:
    config_path = "pyrightconfig.json"  # cspell:ignore pyrightconfig
    if not os.path.exists(config_path):
        return
    with open(config_path) as stream:
        existing_config = json.load(stream)
    for key, value in existing_config.items():
        if isinstance(value, list):
            existing_config[key] = to_toml_array(sorted(value))
    pyproject = load_pyproject()
    tool_table = get_sub_table(pyproject, "tool.pyright", create=True)
    tool_table.update(existing_config)
    write_pyproject(pyproject)
    os.remove(config_path)
    msg = f"Moved pyright configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _update_settings() -> None:
    pyproject = load_pyproject()
    pyright_settings: Table | None = pyproject.get("tool", {}).get("pyright")
    if pyright_settings is None:
        return
    minimal_settings = {
        "typeCheckingMode": "strict",
    }
    if not complies_with_subset(pyright_settings, minimal_settings):
        pyright_settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated pyright configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)
