from pathlib import Path  # noqa: D100

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject, get_constraints_file


def has_constraint_files() -> bool:
    if not CONFIG_PATH.pip_constraints.exists():
        return False
    python_versions = Pyproject.load().get_supported_python_versions()
    constraint_files = [get_constraints_file(v) for v in python_versions]
    constraint_paths = [Path(path) for path in constraint_files if path is not None]
    return any(path.exists() for path in constraint_paths)
