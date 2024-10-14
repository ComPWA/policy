"""Perform updates on the :file:`pyproject.toml` file."""

from __future__ import annotations

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
        _update_requires_python(pyproject)
        _update_python_version_classifiers(pyproject, excluded_python_versions, no_pypi)


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
