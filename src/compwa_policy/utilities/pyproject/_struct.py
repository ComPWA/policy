"""This module is hidden Sphinx can't handle `typing.TypedDict` with hyphens.

See https://github.com/sphinx-doc/sphinx/issues/11039.
"""

import sys
from typing import Dict, List

if sys.version_info < (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict
if sys.version_info < (3, 11):
    from typing_extensions import NotRequired
else:
    from typing import NotRequired

PyprojectTOML = TypedDict(
    "PyprojectTOML",
    {
        "build-system": NotRequired["BuildSystem"],
        "project": "Project",
        "tool": NotRequired[Dict[str, Dict[str, str]]],
    },
)
"""Structure of a `pyproject.toml` file.

See [pyproject.toml
specification](https://packaging.python.org/en/latest/specifications/pyproject-toml).
"""


BuildSystem = TypedDict(
    "BuildSystem",
    {
        "requires": List[str],
        "build-backend": str,
    },
)


Project = TypedDict(
    "Project",
    {
        "name": str,
        "version": NotRequired[str],
        "dependencies": NotRequired[List[str]],
        "optional-dependencies": NotRequired[Dict[str, List[str]]],
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
