# noqa: D100
from __future__ import annotations

import re
from pathlib import Path

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject, get_constraints_file


def has_constraint_files() -> bool:
    if not CONFIG_PATH.pip_constraints.exists():
        return False
    python_versions = Pyproject.load().get_supported_python_versions()
    constraint_files = [get_constraints_file(v) for v in python_versions]
    constraint_paths = [Path(path) for path in constraint_files if path is not None]
    return any(path.exists() for path in constraint_paths)


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
