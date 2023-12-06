"""Update the :file:`environment.yml` Conda environment file."""

from pathlib import Path
from typing import TYPE_CHECKING

from repoma.errors import PrecommitError
from repoma.utilities.project_info import PythonVersion
from repoma.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap, CommentedSeq


def main(python_version: PythonVersion) -> None:
    _update_conda_environment(python_version)


def _update_conda_environment(python_version: PythonVersion) -> None:
    path = Path("environment.yml")
    if not path.exists():
        return
    yaml = create_prettier_round_trip_yaml()
    conda_env: CommentedMap = yaml.load(path)
    dependencies: CommentedSeq = conda_env.get("dependencies", [])
    idx = None
    for i, dep in enumerate(dependencies):
        if not isinstance(dep, str):
            continue
        if dep.strip().startswith("python"):
            idx = i
            break
    if idx is None:
        return
    expected = f"python=={python_version}.*"
    if dependencies[idx] == expected:
        return
    dependencies[idx] = expected
    yaml.dump(conda_env, path)
    msg = f"Set the Python version in {path} to {python_version}"
    raise PrecommitError(msg)
