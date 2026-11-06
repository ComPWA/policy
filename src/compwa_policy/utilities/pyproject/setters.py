"""Setter functions for a :file:`pyproject.toml` config file."""

from __future__ import annotations

import re
from collections import abc
from itertools import pairwise
from typing import TYPE_CHECKING, Any, cast

import tomlkit

from compwa_policy.utilities.pyproject.getters import get_package_name
from compwa_policy.utilities.pyproject.getters import (
    get_sub_table as get_immutable_sub_table,
)
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping, Sequence

    from tomlkit.items import Table

    from compwa_policy.utilities.collections import ExplicitCollection
    from compwa_policy.utilities.pyproject._struct import IncludeGroup, PyprojectTOML


def add_dependency(
    pyproject: PyprojectTOML,
    requirement: str,
    group: str | Sequence[str] | None = None,
    extra: str | Sequence[str] | None = None,
) -> bool:
    if extra is None and group is None:
        return _add_direct_dependency(pyproject, requirement)
    if group is not None:
        return _add_to_dependency_group(pyproject, requirement, group)
    if extra is not None:
        return _add_to_optional_dependencies(pyproject, requirement, extra)
    return False


def _add_direct_dependency(pyproject: PyprojectTOML, requirement: str) -> bool:
    project = get_sub_table(pyproject, "project")
    existing_dependencies = set(project.get("dependencies", []))
    if requirement in existing_dependencies:
        return False
    existing_dependencies.add(requirement)
    project["dependencies"] = to_toml_array(_sort_taplo(existing_dependencies))
    return True


def _add_to_dependency_group(
    pyproject: PyprojectTOML, requirement: str, group: str | Sequence[str]
) -> bool:
    if "dependency-groups" not in pyproject:
        pyproject["dependency-groups"] = tomlkit.table(is_super_table=False)
    dependency_groups = pyproject["dependency-groups"]
    if isinstance(group, str):
        dependencies = dependency_groups.get(group, [])
        if requirement in dependencies:
            return False
        dependencies.append(requirement)
        dependency_groups[group] = to_toml_array(dependencies)
        return True
    if isinstance(group, abc.Sequence) and len(group):
        updated = add_dependency(pyproject, requirement, group[0])
        for previous, current in pairwise(group):
            dependencies = dependency_groups.get(current, [])
            expected: IncludeGroup = {"include-group": previous}
            if expected in dependencies:
                continue
            updated &= True
            dependencies.append(expected)
        return updated
    msg = f"Unsupported type for dependency group: {type(group)}"
    raise NotImplementedError(msg)


def _add_to_optional_dependencies(
    pyproject: PyprojectTOML, requirement: str, extra: str | Sequence[str]
) -> bool:
    if isinstance(extra, str):
        table_key = "project.optional-dependencies"
        optional_dependencies = get_sub_table(pyproject, table_key)
        existing_dependencies = set(optional_dependencies.get(extra, []))
        if requirement in existing_dependencies:
            return False
        existing_dependencies.add(requirement)
        existing_dependencies = set(existing_dependencies)
        optional_dependencies[extra] = to_toml_array(_sort_taplo(existing_dependencies))
        return True
    if isinstance(extra, abc.Sequence):
        if len(extra) == 0:
            msg = "Need at least one key to define nested optional dependencies"
            raise ValueError(msg)
        this_package = get_package_name(pyproject, raise_on_missing=True)
        updated = False
        updated &= add_dependency(pyproject, requirement, extra=extra[0])
        for previous, key in pairwise(extra):
            updated &= add_dependency(
                pyproject, f"{this_package}[{previous}]", extra=key
            )
        return updated
    msg = f"Unsupported type for extra: {type(extra)}"
    raise NotImplementedError(msg)


def _sort_taplo(items: ExplicitCollection[str]) -> list[str]:
    return sorted(items, key=lambda s: ('"' in s, s))


def create_sub_table(config: Mapping[str, Any], /, dotted_header: str) -> Table:
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
    config: Mapping[str, Any], /, dotted_header: str
) -> MutableMapping[str, Any]:
    create_sub_table(config, dotted_header)
    table = get_immutable_sub_table(config, dotted_header)
    return cast("MutableMapping[str, Any]", table)


def remove_dependency(  # ruff: ignore[complex-structure, too-many-branches]
    pyproject: PyprojectTOML,
    package: str,
    ignored_sections: ExplicitCollection[str] | None = None,
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
    >>> split_dependency_definition("python-lsp-server[rope]")
    ('python-lsp-server[rope]', '', '')
    """
    matches = re.match(r"^([a-zA-Z0-9_\[\]-]+)([\!<=>~\s]*)([^ ^#]*)", definition)
    if not matches:
        msg = f"Could not extract package name and version from {definition}"
        raise ValueError(msg)
    package, operator, version = matches.groups()
    return package.strip(), operator.strip(), version.strip()
