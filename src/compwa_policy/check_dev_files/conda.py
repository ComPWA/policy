"""Update the :file:`environment.yml` Conda environment file."""

from __future__ import annotations

from typing import Literal

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import PlainScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, remove_lines
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import (
    Pyproject,
    PythonVersion,
    get_build_system,
    get_constraints_file,
)
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

PackageManagerChoice = Literal["none", "uv", "conda", "pixi", "venv"]
"""Package managers you want to develop the project with."""


def main(python_version: PythonVersion, package_manager: PackageManagerChoice) -> None:
    if package_manager == "conda":
        update_conda_environment(python_version)
    else:
        _remove_conda_configuration()


def update_conda_environment(python_version: PythonVersion) -> None:
    if get_build_system() is None:
        return
    yaml = create_prettier_round_trip_yaml()
    updated = False
    if CONFIG_PATH.conda.exists():
        conda_env: CommentedMap = yaml.load(CONFIG_PATH.conda)
    else:
        conda_env = __create_conda_environment(python_version)
        updated = True
    if "dependencies" not in conda_env:
        conda_env["dependencies"] = CommentedSeq()
    conda_deps: CommentedSeq = conda_env["dependencies"]
    updated |= __update_python_version(python_version, conda_deps)
    updated |= __update_pip_dependencies(python_version, conda_deps)
    if updated:
        yaml.dump(conda_env, CONFIG_PATH.conda)
        msg = f"Updated Conda environment for Python {python_version}"
        raise PrecommitError(msg)


def __create_conda_environment(python_version: PythonVersion) -> CommentedMap:
    return CommentedMap({
        "name": Pyproject.load().get_package_name(),
        "channels": ["defaults"],
        "dependencies": [
            f"python=={python_version}.*",
            "pip",
            {"pip": ["-e .[dev]"]},
        ],
    })


def __update_python_version(version: PythonVersion, conda_deps: CommentedSeq) -> bool:
    idx = __find_python_dependency_index(conda_deps)
    expected = f"python=={version}.*"
    if idx is not None and conda_deps[idx] != expected:
        conda_deps[idx] = expected
        return True
    return False


def __update_pip_dependencies(version: PythonVersion, conda_deps: CommentedSeq) -> bool:
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


def _remove_conda_configuration() -> None:
    with Executor() as do:
        do(__remove_environment_yml)
        # cspell:ignore condaenv
        do(remove_lines, CONFIG_PATH.gitignore, r".*condaenv.*")
        do(remove_lines, CONFIG_PATH.gitignore, r".*environment\.yml.*")


def __remove_environment_yml() -> None:
    if not CONFIG_PATH.conda.exists():
        return
    CONFIG_PATH.conda.unlink()
    msg = (
        "Removed Conda configuration, because conda was not selected as package manager"
    )
    raise PrecommitError(msg)
