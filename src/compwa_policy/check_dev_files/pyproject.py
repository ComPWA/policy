"""Perform updates on the :file:`pyproject.toml` file."""

from __future__ import annotations

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.pyproject.getters import PYTHON_VERSIONS
from compwa_policy.utilities.toml import to_toml_array


def main(excluded_python_versions: set[str]) -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    with ModifiablePyproject.load() as pyproject:
        _update_python_version_classifiers(pyproject, excluded_python_versions)


def _update_python_version_classifiers(
    pyproject: ModifiablePyproject, excluded_python_versions: set[str]
) -> None:
    if not pyproject.has_table("project"):
        return
    project = pyproject.get_table("project")
    requires_python = project.get("requires-python")
    if requires_python is None:
        return
    prefix = "Programming Language :: Python :: "
    expected_version_classifiers = [
        f"{prefix}{v}"
        for v in __get_allowed_versions(requires_python, excluded_python_versions)
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


def __get_allowed_versions(
    version_range: str, exclude: set[str] | None = None
) -> list[str]:
    """Get a list of allowed versions from a version range specifier.

    >>> __get_allowed_versions(">=3.9,<3.13")
    ['3.10', '3.11', '3.12', '3.9']
    >>> __get_allowed_versions(">=3.9", exclude={"3.9"})
    ['3.10', '3.11', '3.12']
    """
    specifier = SpecifierSet(version_range)
    versions_to_check = [Version(v) for v in sorted(PYTHON_VERSIONS)]
    allowed_versions = [str(v) for v in versions_to_check if v in specifier]
    if exclude is not None:
        return [v for v in allowed_versions if v not in exclude]
    return allowed_versions
