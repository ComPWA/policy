"""Tools for loading, inspecting, and updating :code:`pyproject.toml`."""
import os
from typing import Any, Iterable, Optional

import tomlkit
from tomlkit.container import Container
from tomlkit.items import Array, Table
from tomlkit.toml_document import TOMLDocument

from repoma.utilities import CONFIG_PATH


def complies_with_subset(settings: dict, minimal_settings: dict) -> bool:
    return all(settings.get(key) == value for key, value in minimal_settings.items())


def load_pyproject(content: Optional[str] = None) -> TOMLDocument:
    if not os.path.exists(CONFIG_PATH.pyproject):
        return TOMLDocument()
    if content is None:
        with open(CONFIG_PATH.pyproject) as stream:
            return tomlkit.loads(stream.read())
    return tomlkit.loads(content)


def get_sub_table(config: Container, dotted_header: str, create: bool = False) -> Table:
    """Get a TOML sub-table through a dotted header key."""
    current_table: Any = config
    for header in dotted_header.split("."):
        if header not in current_table:
            if create:
                current_table[header] = tomlkit.table()
            else:
                msg = f"TOML data does not contain {dotted_header!r}"
                raise KeyError(msg)
        current_table = current_table[header]
    return current_table


def write_pyproject(config: TOMLDocument) -> None:
    src = tomlkit.dumps(config, sort_keys=True)
    with open(CONFIG_PATH.pyproject, "w") as stream:
        stream.write(src)


def to_toml_array(items: Iterable[Any]) -> Array:
    array = tomlkit.array()
    array.extend(items)
    if len(array) > 1:
        array.multiline(True)
    return array
