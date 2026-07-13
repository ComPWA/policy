"""Update the :file:`environment.yml` Conda environment file."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import PlainScalarString

from compwa_policy.utilities import CONFIG_PATH, remove_lines
from compwa_policy.utilities.pyproject import (
    PythonVersion,
    get_constraints_file,
    has_pyproject_package_name,
)
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Changelog, Session

PackageManagerChoice = Literal["none", "uv", "conda", "pixi+uv", "pixi", "venv"]
"""Package managers you want to develop the project with."""


def main(
    session: Session,
    python_version: PythonVersion,
    package_manager: PackageManagerChoice,
) -> None:
    if package_manager == "conda":
        update_conda_environment(session, python_version)
    else:
        _remove_conda_configuration(session)


def update_conda_environment(
    session: Session,
    /,
    python_version: PythonVersion,
) -> None:
    if not has_pyproject_package_name(session):
        return
    yaml = create_prettier_round_trip_yaml()
    updated = False
    if CONFIG_PATH.conda.exists():
        conda_env: CommentedMap = yaml.load(CONFIG_PATH.conda)
    else:
        conda_env = __create_conda_environment(session, python_version)
        updated = True
    if "dependencies" not in conda_env:
        conda_env["dependencies"] = CommentedSeq()
    conda_deps: CommentedSeq = conda_env["dependencies"]
    updated |= __update_python_version(python_version, conda_deps)
    updated |= __update_pip_dependencies(python_version, conda_deps)
    if updated:
        yaml.dump(conda_env, CONFIG_PATH.conda)
        msg = f"Updated Conda environment for Python {python_version}"
        session.changelog.append(msg)


def __create_conda_environment(
    session: Session,
    /,
    python_version: PythonVersion,
) -> CommentedMap:
    pyproject = session.pyproject
    package_name = pyproject.get_package_name() if pyproject is not None else None
    return CommentedMap({
        "name": str(package_name) if package_name is not None else None,
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


def _remove_conda_configuration(session: Session, /) -> None:
    session.changelog += __remove_environment_yml()
    # cspell:ignore condaenv
    remove_lines(session, CONFIG_PATH.gitignore, r".*condaenv.*")
    remove_lines(session, CONFIG_PATH.gitignore, r".*environment\.yml.*")


def __remove_environment_yml() -> Changelog:
    if not CONFIG_PATH.conda.exists():
        return []
    CONFIG_PATH.conda.unlink()
    msg = (
        "Removed Conda configuration, because conda was not selected as package manager"
    )
    return [msg]
