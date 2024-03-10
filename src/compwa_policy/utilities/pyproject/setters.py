"""Setter functions for a :file:`pyproject.toml` config file."""

from __future__ import annotations

from collections import abc
from typing import TYPE_CHECKING, Any, Iterable, Mapping, MutableMapping, Sequence, cast

import tomlkit

from compwa_policy.utilities.pyproject.getters import get_package_name
from compwa_policy.utilities.pyproject.getters import (
    get_sub_table as get_immutable_sub_table,
)
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from tomlkit.items import Table

    from compwa_policy.utilities.pyproject._struct import PyprojectTOML


def add_dependency(
    pyproject: PyprojectTOML,
    package: str,
    optional_key: str | Sequence[str] | None = None,
) -> bool:
    if optional_key is None:
        project = get_sub_table(pyproject, "project")
        existing_dependencies: set[str] = set(project.get("dependencies", []))
        if package in existing_dependencies:
            return False
        existing_dependencies.add(package)
        project["dependencies"] = to_toml_array(_sort_taplo(existing_dependencies))
        return True
    if isinstance(optional_key, str):
        table_key = "project.optional-dependencies"
        optional_dependencies = get_sub_table(pyproject, table_key)
        existing_dependencies = set(optional_dependencies.get(optional_key, []))
        if package in existing_dependencies:
            return False
        existing_dependencies.add(package)
        existing_dependencies = set(existing_dependencies)
        optional_dependencies[optional_key] = to_toml_array(
            _sort_taplo(existing_dependencies)
        )
        return True
    if isinstance(optional_key, abc.Sequence):
        if len(optional_key) < 2:  # noqa: PLR2004
            msg = "Need at least two keys to define nested optional dependencies"
            raise ValueError(msg)
        this_package = get_package_name(pyproject, raise_on_missing=True)
        updated = False
        for key, previous in zip(optional_key, [None, *optional_key]):
            if previous is None:
                updated &= add_dependency(pyproject, package, key)
            else:
                updated &= add_dependency(pyproject, f"{this_package}[{previous}]", key)
        return updated
    msg = f"Unsupported type for optional_key: {type(optional_key)}"
    raise NotImplementedError(msg)


def _sort_taplo(items: Iterable[str]) -> list[str]:
    return sorted(items, key=lambda s: ('"' in s, s))


def create_sub_table(config: Mapping[str, Any], dotted_header: str) -> Table:
    """Create a TOML sub-table through a dotted header key."""
    current_table: Any = config
    for header in dotted_header.split("."):
        if header not in current_table:
            current_table[header] = tomlkit.table()
        current_table = current_table[header]
    return current_table


def get_sub_table(
    config: Mapping[str, Any], dotted_header: str
) -> MutableMapping[str, Any]:
    create_sub_table(config, dotted_header)
    table = get_immutable_sub_table(config, dotted_header)
    return cast(MutableMapping[str, Any], table)


def remove_dependency(
    pyproject: PyprojectTOML,
    package: str,
    ignored_sections: Iterable[str] | None = None,
) -> bool:
    project = pyproject.get("project")
    if project is None:
        return False
    updated = False
    dependencies = project.get("dependencies")
    if dependencies is not None and package in dependencies:
        dependencies.remove(package)
        updated = True
    optional_dependencies = project.get("optional-dependencies")
    if optional_dependencies is not None:
        if ignored_sections is None:
            ignored_sections = set()
        else:
            ignored_sections = set(ignored_sections)
        for section, values in optional_dependencies.items():
            if section in ignored_sections:
                continue
            if package in values:
                values.remove(package)
                updated = True
        if updated:
            empty_sections = [k for k, v in optional_dependencies.items() if not v]
            for section in empty_sections:
                del optional_dependencies[section]
    return updated
