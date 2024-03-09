"""Update the :file:`environment.yml` Conda environment file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruamel.yaml.scalarstring import PlainScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import (
    PythonVersion,
    get_build_system,
    get_constraints_file,
)
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap, CommentedSeq


def main(python_version: PythonVersion) -> None:
    if not CONFIG_PATH.conda.exists():
        return
    if get_build_system() is None:
        return
    yaml = create_prettier_round_trip_yaml()
    conda_env: CommentedMap = yaml.load(CONFIG_PATH.conda)
    conda_deps: CommentedSeq = conda_env.get("dependencies", [])

    updated = _update_python_version(python_version, conda_deps)
    updated |= _update_pip_dependencies(python_version, conda_deps)
    if updated:
        yaml.dump(conda_env, CONFIG_PATH.conda)
        msg = f"Set the Python version in {CONFIG_PATH.conda} to {python_version}"
        raise PrecommitError(msg)


def _update_python_version(version: PythonVersion, conda_deps: CommentedSeq) -> bool:
    idx = __find_python_dependency_index(conda_deps)
    expected = f"python=={version}.*"
    if idx is not None and conda_deps[idx] != expected:
        conda_deps[idx] = expected
        return True
    return False


def _update_pip_dependencies(version: PythonVersion, conda_deps: CommentedSeq) -> bool:
    pip_deps = __get_pip_dependencies(conda_deps)
    if pip_deps is None:
        return False
    constraints_file = get_constraints_file(version)
    if constraints_file is None:
        expected_pip = "-e .[dev]"
    else:
        expected_pip = f"-c {constraints_file} -e .[dev]"
    if len(pip_deps) and pip_deps[0] != expected_pip:
        pip_deps[0] = PlainScalarString(expected_pip)
        return True
    return False


def __find_python_dependency_index(dependencies: CommentedSeq) -> int | None:
    for i, dep in enumerate(dependencies):
        if not isinstance(dep, str):
            continue
        if dep.strip().startswith("python"):
            return i
    return None


def __get_pip_dependencies(dependencies: CommentedSeq) -> CommentedSeq | None:
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue
        pip_deps = dep.get("pip")
        if pip_deps is not None and isinstance(pip_deps, list):
            return pip_deps
    return None
