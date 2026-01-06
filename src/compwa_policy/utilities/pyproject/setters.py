"""Setter functions for a :file:`pyproject.toml` config file."""

from __future__ import annotations

import re
import sys
from collections import abc
from typing import TYPE_CHECKING, Any, cast

import tomlkit

from compwa_policy.utilities.pyproject.getters import get_package_name
from compwa_policy.utilities.pyproject.getters import (
    get_sub_table as get_immutable_sub_table,
)
from compwa_policy.utilities.toml import to_toml_array

if sys.version_info >= (3, 10):
    from itertools import pairwise
else:
    from more_itertools import pairwise
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, MutableMapping, Sequence

    from tomlkit.items import Table

    from compwa_policy.utilities.pyproject._struct import IncludeGroup, PyprojectTOML


def add_dependency(
    pyproject: PyprojectTOML,
    package: str,
    dependency_group: str | Sequence[str] | None = None,
    optional_key: str | Sequence[str] | None = None,
) -> bool:
    if optional_key is None and dependency_group is None:
        return _add_direct_dependency(pyproject, package)
    if dependency_group is not None:
        return _add_to_dependency_group(pyproject, package, dependency_group)
    if optional_key is not None:
        return _add_to_optional_dependencies(pyproject, package, optional_key)
    return False


def _add_direct_dependency(pyproject: PyprojectTOML, package: str) -> bool:
    project = get_sub_table(pyproject, "project")
    existing_dependencies = set(project.get("dependencies", []))
    if package in existing_dependencies:
        return False
    existing_dependencies.add(package)
    project["dependencies"] = to_toml_array(_sort_taplo(existing_dependencies))
    return True


def _add_to_dependency_group(
    pyproject: PyprojectTOML, package: str, dependency_group: str | Sequence[str]
) -> bool:
    if "dependency-groups" not in pyproject:
        pyproject["dependency-groups"] = tomlkit.table(is_super_table=False)
    dependency_groups = pyproject["dependency-groups"]
    if isinstance(dependency_group, str):
        dependencies = dependency_groups.get(dependency_group, [])
        if package in dependencies:
            return False
        dependencies.append(package)
        dependency_groups[dependency_group] = to_toml_array(dependencies)
        return True
    if isinstance(dependency_group, abc.Sequence) and len(dependency_group):
        updated = add_dependency(pyproject, package, dependency_group[0])
        for previous, current in pairwise(dependency_group):
            dependencies = dependency_groups.get(current, [])
            expected: IncludeGroup = {"include-group": previous}
            if expected in dependencies:
                continue
            updated &= True
            dependencies.append(expected)
        return updated
    msg = f"Unsupported type for dependency group: {type(dependency_group)}"
    raise NotImplementedError(msg)


def _add_to_optional_dependencies(
    pyproject: PyprojectTOML, package: str, optional_key: str | Sequence[str]
) -> bool:
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
        if len(optional_key) == 0:
            msg = "Need at least one key to define nested optional dependencies"
            raise ValueError(msg)
        this_package = get_package_name(pyproject, raise_on_missing=True)
        updated = False
        updated &= add_dependency(pyproject, package, optional_key=optional_key[0])
        for previous, key in pairwise(optional_key):
            updated &= add_dependency(
                pyproject, f"{this_package}[{previous}]", optional_key=key
            )
        return updated
    msg = f"Unsupported type for optional_key: {type(optional_key)}"
    raise NotImplementedError(msg)


def _sort_taplo(items: Iterable[str]) -> list[str]:
    return sorted(items, key=lambda s: ('"' in s, s))


def create_sub_table(config: Mapping[str, Any], dotted_header: str) -> Table:
    """Create a TOML sub-table through a dotted header key."""
    current_table = cast("Any", config)
    header_hierarchy = dotted_header.split(".")
    for i, header in enumerate(header_hierarchy, 1):
        if header not in current_table:
            is_last_header = i == len(header_hierarchy)
            current_table[header] = tomlkit.table(is_super_table=not is_last_header)
        current_table = current_table[header]
    return current_table


def get_sub_table(
    config: Mapping[str, Any], dotted_header: str
) -> MutableMapping[str, Any]:
    create_sub_table(config, dotted_header)
    table = get_immutable_sub_table(config, dotted_header)
    return cast("MutableMapping[str, Any]", table)


def remove_dependency(  # noqa: C901, PLR0912
    pyproject: PyprojectTOML,
    package: str,
    ignored_sections: Iterable[str] | None = None,
) -> bool:
    project = pyproject.get("project")
    if project is None:
        return False
    updated = False
    dependencies = project.get("dependencies")
    if dependencies is not None:
        package_names = [split_dependency_definition(p)[0] for p in dependencies]
        if package in set(package_names):
            idx = package_names.index(package)
            dependencies.pop(idx)
            updated = True
    if ignored_sections is None:
        ignored_sections = set()
    else:
        ignored_sections = set(ignored_sections)
    optional_dependencies = project.get("optional-dependencies")
    if optional_dependencies is not None:
        for section, dependencies in optional_dependencies.items():
            if section in ignored_sections:
                continue
            package_names = [split_dependency_definition(p)[0] for p in dependencies]
            if package in set(package_names):
                idx = package_names.index(package)
                dependencies.pop(idx)
                updated = True
        if updated:
            empty_sections = [k for k, v in optional_dependencies.items() if not v]
            for section in empty_sections:
                del optional_dependencies[section]
            if not optional_dependencies:
                del project["optional-dependencies"]
    dependency_groups = pyproject.get("dependency-groups")
    if dependency_groups is not None:
        for section, dependencies in dependency_groups.items():
            if section in ignored_sections:
                continue
            package_names = [
                split_dependency_definition(p)[0] if isinstance(p, str) else p
                for p in dependencies
            ]
            if package in package_names:
                idx = package_names.index(package)
                dependencies.pop(idx)
                updated = True
        if updated:
            empty_sections = [k for k, v in dependency_groups.items() if not v]
            for section in empty_sections:
                del dependency_groups[section]
            if not dependency_groups:
                del pyproject["dependency-groups"]
    return updated


def split_dependency_definition(definition: str) -> tuple[str, str, str]:
    """Get the package name, operator, and version from a PyPI dependency definition.

    >>> split_dependency_definition("julia")
    ('julia', '', '')
    >>> split_dependency_definition("python==3.9.*")
    ('python', '==', '3.9.*')
    >>> split_dependency_definition("graphviz  # for binder")
    ('graphviz', '', '')
    >>> split_dependency_definition("pip > 19  # needed")
    ('pip', '>', '19')
    >>> split_dependency_definition("compwa-policy!= 3.14")
    ('compwa-policy', '!=', '3.14')
    >>> split_dependency_definition("my_package~=1.2")
    ('my_package', '~=', '1.2')
    >>> split_dependency_definition("any_version_package==*")
    ('any_version_package', '==', '*')
    """
    matches = re.match(r"^([a-zA-Z0-9_-]+)([\!<=>~\s]*)([^ ^#]*)", definition)
    if not matches:
        msg = f"Could not extract package name and version from {definition}"
        raise ValueError(msg)
    package, operator, version = matches.groups()
    return package.strip(), operator.strip(), version.strip()
