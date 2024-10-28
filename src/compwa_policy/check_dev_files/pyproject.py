"""Perform updates on the :file:`pyproject.toml` file."""

from __future__ import annotations

import re

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.pyproject.getters import (
    _get_allowed_versions,
    _get_requires_python,
)
from compwa_policy.utilities.toml import to_toml_array


def main(excluded_python_versions: set[str], no_pypi: bool) -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    with ModifiablePyproject.load() as pyproject:
        _convert_to_dependency_groups(pyproject)
        _update_requires_python(pyproject)
        _update_python_version_classifiers(pyproject, excluded_python_versions, no_pypi)


def _convert_to_dependency_groups(pyproject: ModifiablePyproject) -> None:
    table_key = "project.optional-dependencies"
    if not pyproject.has_table(table_key):
        return
    optional_dependencies = pyproject.get_table(table_key)
    dependency_groups = pyproject.get_table("dependency-groups", create=True)
    dev_groups = {
        "dev",
        "doc",
        "jupyter",
        "lint",
        "mypy",
        "notebooks",
        "sty",
        "test",
        "types",
    }
    package_name = pyproject.get_package_name()
    updated = False
    for group, dependencies in dict(optional_dependencies).items():
        if group not in dev_groups:
            continue
        dependencies = __convert_to_dependency_group(
            dependencies, package_name, dev_groups
        )
        dependency_groups[group] = to_toml_array(dependencies)
        optional_dependencies.pop(group)
        updated = True
    if len(optional_dependencies) == 0:
        del pyproject.get_table("project")["optional-dependencies"]
    if updated:
        msg = "Converted optional-dependencies to dependency-groups"
        pyproject.changelog.append(msg)


def __convert_to_dependency_group(
    dependencies: list[str], package_name: str | None, dev_dependencies: set[str]
) -> list[str | dict]:
    """Convert a list of optional dependencies to a dependency group.

    >>> __convert_to_dependency_group(
    ...     ["qrules[dev]", "qrules[viz]", "mypy"],
    ...     package_name="qrules",
    ...     dev_dependencies={"dev"},
    ... )
    [{'include-group': 'dev'}, 'qrules[viz]', 'mypy']
    """
    new_dependencies = []
    for dependency in dependencies:
        converted = __convert_to_include(dependency, package_name, dev_dependencies)
        if converted is not None:
            new_dependencies.append(converted)
    return new_dependencies


def __convert_to_include(
    dependency: str, package_name: str | None, dev_dependencies: set[str]
) -> str | dict | None:
    """Convert a recursive optional dependency to an include group entry.

    >>> __convert_to_include("compwa-policy[dev]", "compwa-policy", {"dev"})
    {'include-group': 'dev'}
    >>> __convert_to_include("ruff", "compwa-policy", {"dev"})
    'ruff'
    >>> __convert_to_include("qrules[viz]", "qrules", {"dev"})
    'qrules[viz]'
    """
    if package_name is not None:
        matches = re.match(rf"{package_name}\[(.+)\]", dependency)
        if matches is not None:
            include_name = matches.group(1)
            if include_name in dev_dependencies:
                return {"include-group": include_name}
    return dependency


def _update_requires_python(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("project"):
        return
    project = pyproject.get_table("project")
    if "requires-python" in project:
        return
    requires_python = _get_requires_python(project)
    if requires_python:
        minimal_version, *_ = _get_allowed_versions(requires_python)
        requires_python = f">={minimal_version}"
        project["requires-python"] = requires_python
        pyproject.changelog.append(f'Set requires-python = "{requires_python}" field')


def _update_python_version_classifiers(
    pyproject: ModifiablePyproject, excluded_python_versions: set[str], no_pypi: bool
) -> None:
    if not pyproject.has_table("project"):
        return
    project = pyproject.get_table("project")
    if no_pypi:
        if "classifiers" in project:
            del project["classifiers"]
            msg = "Removed Python version classifiers because of --no-pypi"
            pyproject.changelog.append(msg)
    else:
        requires_python = _get_requires_python(project)
        if not requires_python:
            return
        prefix = "Programming Language :: Python :: "
        expected_version_classifiers = [
            f"{prefix}{v}"
            for v in _get_allowed_versions(requires_python, excluded_python_versions)
        ]
        existing_classifiers = __get_existing_classifiers(pyproject)
        merged_classifiers = {
            classifier
            for classifier in existing_classifiers
            if not classifier.startswith(f"{prefix}3.")
        } | set(expected_version_classifiers)
        if set(existing_classifiers) != merged_classifiers:
            project["classifiers"] = to_toml_array(sorted(merged_classifiers))
            pyproject.changelog.append("Updated Python version classifiers")


def __get_existing_classifiers(pyproject: ModifiablePyproject) -> list[str]:
    if not pyproject.has_table("project"):
        return []
    project = pyproject.get_table("project")
    return project.get("classifiers", [])
