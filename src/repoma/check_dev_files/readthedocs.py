"""Update Read the Docs configuration."""

from typing import TYPE_CHECKING

from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.project_info import PythonVersion, get_constraints_file
from repoma.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap, CommentedSeq


def main(python_version: PythonVersion) -> None:
    if not CONFIG_PATH.readthedocs.exists():
        return
    executor = Executor()
    executor(_update_python_version, python_version)
    executor(_update_install_step, python_version)
    executor.finalize()


def _update_python_version(python_version: PythonVersion) -> None:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.readthedocs)
    tools: CommentedMap = config.get("build", {}).get("tools", {})
    if tools is None:
        return
    existing_version = tools.get("python")
    if existing_version is None:
        return
    expected_version = DoubleQuotedScalarString(python_version)
    if expected_version == existing_version:
        return
    tools["python"] = expected_version
    yaml.dump(config, CONFIG_PATH.readthedocs)
    msg = f"Switched to Python {python_version} in {CONFIG_PATH.readthedocs}"
    raise PrecommitError(msg)


def _update_install_step(python_version: PythonVersion) -> None:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.readthedocs)
    steps: CommentedSeq = config.get("build", {}).get("jobs", {}).get("post_install")
    if steps is None:
        return
    if len(steps) == 0:
        return
    constraints_file = get_constraints_file(python_version)
    if constraints_file is None:
        expected_install = "pip install -e .[doc]"
    else:
        expected_install = f"pip install -c {constraints_file} -e .[doc]"
    if steps[0] == expected_install:
        return
    steps[0] = expected_install
    yaml.dump(config, CONFIG_PATH.readthedocs)
    msg = f"Pinned constraints for Python {python_version} in {CONFIG_PATH.readthedocs}"
    raise PrecommitError(msg)
