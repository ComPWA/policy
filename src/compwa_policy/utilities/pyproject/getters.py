"""Getter implementations for :class:`.PyprojectTOML`."""

from __future__ import annotations

import sys
from textwrap import dedent
from typing import TYPE_CHECKING, Any, overload

from compwa_policy.errors import PrecommitError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from compwa_policy.utilities.pyproject._struct import ProjectURLs, PyprojectTOML

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


PythonVersion = Literal["3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12"]


@overload
def get_package_name(doc: PyprojectTOML) -> str | None: ...
@overload
def get_package_name(
    doc: PyprojectTOML, raise_on_missing: Literal[False]
) -> str | None: ...
@overload
def get_package_name(doc: PyprojectTOML, raise_on_missing: Literal[True]) -> str: ...
def get_package_name(doc: PyprojectTOML, raise_on_missing: bool = False):  # type: ignore[no-untyped-def]
    if not has_sub_table(doc, "project"):
        if raise_on_missing:
            msg = "Please provide a name for the package under the [project] table in pyproject.toml"
            raise PrecommitError(msg)
        return None
    project = get_sub_table(doc, "project")
    package_name = project.get("name")
    if package_name is None:
        return None
    return package_name


def get_project_urls(pyproject: PyprojectTOML) -> ProjectURLs:
    project_table = get_sub_table(pyproject, "project")
    urls = project_table.get("urls")
    if urls is None:
        msg = """
            pyproject.toml does not contain project URLs. Should be something like:

                [project.urls]
                Documentation = "https://ampform.rtfd.io"
                Source = "https://github.com/ComPWA/ampform"
                Tracker = "https://github.com/ComPWA/ampform/issues"
        """
        msg = dedent(msg)
        raise PrecommitError(msg)
    return urls


def get_source_url(pyproject: PyprojectTOML) -> str:
    urls = get_project_urls(pyproject)
    source_url = urls.get("Source")
    if source_url is None:
        msg = '[project.urls] in pyproject.toml does not contain a "Source" URL'
        raise PrecommitError(msg)
    return source_url


def get_supported_python_versions(pyproject: PyprojectTOML) -> list[PythonVersion]:
    """Extract sorted list of supported Python versions from package classifiers.

    >>> import tomlkit
    >>> pyproject = tomlkit.loads('''
    ...     [project]
    ...     classifiers = [
    ...         "Programming Language :: Python :: 3.9",
    ...         "Programming Language :: Python :: 3.10",
    ...         "Programming Language :: Python :: 3.11",
    ...     ]
    ... ''')
    >>> get_supported_python_versions(pyproject)
    ['3.9', '3.10', '3.11']
    """
    if not has_sub_table(pyproject, "project"):
        return []
    project_table = get_sub_table(pyproject, "project")
    classifiers = project_table.get("classifiers", [])
    python_versions = _extract_python_versions(classifiers)
    if not python_versions:
        msg = "Could not determine Python version classifiers of this package"
        raise PrecommitError(msg)
    return sorted(python_versions, key=lambda s: tuple(int(i) for i in s.split(".")))


def _extract_python_versions(classifiers: list[str]) -> list[PythonVersion]:
    """Extract Python versions from `PyPI classifiers <https://pypi.org/classifiers>`_.

    >>> classifiers = [
    ...     "License :: OSI Approved :: MIT License",
    ...     "Programming Language :: Python :: 3.7",
    ...     "Programming Language :: Python :: 3.8",
    ...     "Programming Language :: Python :: 3.9",
    ...     "Programming Language :: Python :: 3.10",
    ...     "Programming Language :: Python :: 3.11",
    ...     "Programming Language :: Python :: 3.12",
    ... ]
    >>> _extract_python_versions(classifiers)
    ['3.7', '3.8', '3.9', '3.10', '3.11', '3.12']
    """
    identifier = "Programming Language :: Python :: 3."
    version_classifiers = [s for s in classifiers if s.startswith(identifier)]
    prefix = identifier[:-2]
    return [s.replace(prefix, "") for s in version_classifiers]  # type: ignore[misc]


def get_sub_table(config: Mapping[str, Any], dotted_header: str) -> Mapping[str, Any]:
    """Get a TOML sub-table through a dotted header key."""
    current_table = config
    for header in dotted_header.split("."):
        if header not in current_table:
            msg = f"TOML data does not contain {dotted_header!r}"
            raise KeyError(msg)
        current_table = current_table[header]
    return current_table


def has_sub_table(config: Mapping[str, Any], dotted_header: str) -> bool:
    current_table: Any = config
    for header in dotted_header.split("."):
        if header in current_table:
            current_table = current_table[header]
        else:
            return False
    return True
