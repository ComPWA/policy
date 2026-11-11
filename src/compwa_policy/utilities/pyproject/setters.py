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
    from collections.abc import Mapping, MutableMapping

    from tomlkit.items import Table

    from compwa_policy.utilities.collections import (
        ExplicitCollection,
        OrderedCollection,
    )
    from compwa_policy.utilities.pyproject._struct import IncludeGroup, PyprojectTOML


def add_dependency(
    pyproject: PyprojectTOML,
    /,
    requirement: str,
    *,
    extra: str | OrderedCollection[str] | None = None,
    group: str | OrderedCollection[str] | None = None,
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
    pyproject: PyprojectTOML, requirement: str, group: str | OrderedCollection[str]
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
        updated = add_dependency(pyproject, requirement, group=group[0])
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
    pyproject: PyprojectTOML, requirement: str, extra: str | OrderedCollection[str]
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
    /,
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
            remove_empty_dependency_groups(pyproject)
    return updated


def remove_empty_dependency_groups(pyproject: PyprojectTOML, /) -> list[str]:
    """Remove empty dependency groups and the ``include-group`` entries to them.

    Removing an ``include-group`` entry can leave another group empty, so this repeats
    until no empty group remains. Returns the names of the removed groups.

    >>> import tomlkit
    >>> pyproject = tomlkit.parse(
    ...     '''
    ... [dependency-groups]
    ... dev = ["ruff", {include-group = "doc"}, {include-group = "style"}]
    ... doc = [{include-group = "style"}]
    ... style = []
    ... '''
    ... )
    >>> remove_empty_dependency_groups(pyproject)
    ['style', 'doc']
    >>> pyproject["dependency-groups"].unwrap()
    {'dev': ['ruff']}
    """
    dependency_groups = pyproject.get("dependency-groups")
    if dependency_groups is None:
        return []
    removed: list[str] = []
    while empty_groups := [k for k, v in dependency_groups.items() if not v]:
        for group in empty_groups:
            del dependency_groups[group]
            removed.append(group)
        for dependencies in dependency_groups.values():
            for idx in reversed(range(len(dependencies))):
                dependency = dependencies[idx]
                if (
                    isinstance(dependency, abc.Mapping)
                    and dependency.get("include-group") in empty_groups
                ):
                    dependencies.pop(idx)
    if not dependency_groups:
        del pyproject["dependency-groups"]
    return removed


def split_dependency_definition(requirement: str) -> tuple[str, str, str]:
    """Get the package name, operator, and version from a PyPI dependency requirement.

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
    matches = re.match(r"^([a-zA-Z0-9_\[\]-]+)([\!<=>~\s]*)([^ ^#]*)", requirement)
    if not matches:
        msg = f"Could not extract package name and version from {requirement}"
        raise ValueError(msg)
    package, operator, version = matches.groups()
    return package.strip(), operator.strip(), version.strip()
