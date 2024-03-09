"""Update Read the Docs configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import get_constraints_file
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap, CommentedSeq

    from compwa_policy.utilities.pyproject.getters import PythonVersion


def main(python_version: PythonVersion) -> None:
    if not CONFIG_PATH.readthedocs.exists():
        return
    executor = Executor()
    executor(_update_os)
    executor(_update_python_version, python_version)
    executor(_update_install_step, python_version)
    executor.finalize()


def _update_os() -> None:
    yaml = create_prettier_round_trip_yaml()
    config: CommentedMap = yaml.load(CONFIG_PATH.readthedocs)
    build: CommentedMap | None = config.get("build")
    if build is None:
        return
    os: str | None = build.get("os")
    expected = "ubuntu-22.04"
    if os == expected:
        return
    build["os"] = expected
    yaml.dump(config, CONFIG_PATH.readthedocs)
    msg = f"Switched to {expected} in {CONFIG_PATH.readthedocs}"
    raise PrecommitError(msg)


def _update_python_version(python_version: PythonVersion) -> None:
    yaml = create_prettier_round_trip_yaml()
    config: CommentedMap = yaml.load(CONFIG_PATH.readthedocs)
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
    config: CommentedMap = yaml.load(CONFIG_PATH.readthedocs)
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
