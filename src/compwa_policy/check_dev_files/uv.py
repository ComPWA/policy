"""Update `uv <https://docs.astral.sh/uv>`_ configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.executor import Executor

if TYPE_CHECKING:
    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.utilities.pyproject.getters import PythonVersion


def main(
    dev_python_version: PythonVersion, package_managers: set[PackageManagerChoice]
) -> None:
    if "uv" in package_managers:
        with Executor() as do:
            do(_update_python_version_file, dev_python_version)


def _update_python_version_file(dev_python_version: PythonVersion) -> None:
    python_version_file = Path(".python-version")
    existing_python_version = ""
    if python_version_file.exists():
        with open(python_version_file) as stream:
            existing_python_version = stream.read().strip()
    if existing_python_version == dev_python_version:
        return
    with open(".python-version", "w") as stream:
        stream.write(dev_python_version + "\n")
    msg = f"Updated {python_version_file} to {dev_python_version}"
    raise PrecommitError(msg)
