"""Tools for loading, inspecting, and updating :code:`pyproject.toml`."""

import os
from typing import Any, Iterable, Optional

import tomlkit
from tomlkit.container import Container
from tomlkit.items import Array, Table
from tomlkit.toml_document import TOMLDocument

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.precommit import find_repo, load_round_trip_precommit_config


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


def to_toml_array(items: Iterable[Any], enforce_multiline: bool = False) -> Array:
    array = tomlkit.array()
    array.extend(items)
    if enforce_multiline or len(array) > 1:
        array.multiline(True)
    else:
        array.multiline(False)
    return array


def update_nbqa_settings(key: str, expected: Any) -> None:
    # cspell:ignore addopts
    if not CONFIG_PATH.precommit.exists():
        return
    if not __has_nbqa_precommit_repo():
        return
    pyproject = load_pyproject()
    nbqa_table = get_sub_table(pyproject, "tool.nbqa.addopts", create=True)
    if nbqa_table.get(key) != expected:
        nbqa_table[key] = expected
        write_pyproject(pyproject)
        msg = f"Added nbQA configuration for {key!r}"
        raise PrecommitError(msg)


def __has_nbqa_precommit_repo() -> bool:
    config, _ = load_round_trip_precommit_config()
    nbqa_repo = find_repo(config, "https://github.com/nbQA-dev/nbQA")
    if nbqa_repo is None:
        return False
    return True
