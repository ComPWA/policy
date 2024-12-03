"""This module is hidden Sphinx can't handle `typing.TypedDict` with hyphens.

See https://github.com/sphinx-doc/sphinx/issues/11039.
"""

import sys
from typing import TypedDict

if sys.version_info >= (3, 11):
    from typing import NotRequired
else:
    from typing_extensions import NotRequired

IncludeGroup = TypedDict("IncludeGroup", {"include-group": str})
PyprojectTOML = TypedDict(
    "PyprojectTOML",
    {
        "build-system": NotRequired["BuildSystem"],
        "project": "Project",
        "dependency-groups": NotRequired[dict[str, list[str | IncludeGroup]]],
        "tool": NotRequired[dict[str, dict[str, str]]],
    },
)
"""Structure of a `pyproject.toml` file.

See [pyproject.toml
specification](https://packaging.python.org/en/latest/specifications/pyproject-toml).
"""


BuildSystem = TypedDict(
    "BuildSystem",
    {
        "requires": list[str],
        "build-backend": str,
    },
)


Project = TypedDict(
    "Project",
    {
        "name": str,
        "version": NotRequired[str],
        "dependencies": NotRequired[list[str]],
        "optional-dependencies": NotRequired[dict[str, list[str]]],
        "urls": NotRequired["ProjectURLs"],
    },
)


class ProjectURLs(TypedDict):
    """Project  for PyPI."""

    Changelog: NotRequired[str]
    Documentation: NotRequired[str]
    Homepage: NotRequired[str]
    Issues: NotRequired[str]
    Repository: NotRequired[str]
    Source: NotRequired[str]
    Tracker: NotRequired[str]
