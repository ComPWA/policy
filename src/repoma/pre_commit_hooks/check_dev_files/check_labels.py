"""Check whether the repository (still) contains a ``labels.toml`` file.

If it's still there remove it, because it has been superceded by the
`github.com/ComPWA/meta <https://github.com/ComPWA/meta>`_ repository.
"""

import os
import pathlib
from typing import List

from repoma.pre_commit_hooks.errors import PrecommitError

__LABELS_CONFIG_FILE = "labels.toml"


def check_has_labels(fix: bool) -> None:
    if os.path.exists(__LABELS_CONFIG_FILE):
        message = (
            f'Repository contains a file "{__LABELS_CONFIG_FILE}" for the'
            " labels package (see https://pypi.org/project/labels). This file"
            " should not be there, because labels are maintained through the"
            " https://github.com/ComPWA/meta repository."
        )
        if fix:
            message += " It has been removed."
            os.remove(__LABELS_CONFIG_FILE)
        else:
            message += " Please remove it."
    faulty_req_files = [
        str(file.absolute())
        for file in _get_requirement_files()
        if _check_has_labels_requirement(file)
    ]
    if faulty_req_files:
        message = (
            "Repository lists the labels package"
            " (https://pypi.org/project/labels) as a developer requirement."
        )
        if fix:
            _remove_all_labels_requirement()
            message += " Problems have been fixed, please re-stage files."
        else:
            message += ' Please remove "labels" from the following files:\n  '
            message += "\n  ".join(faulty_req_files)
        raise PrecommitError(message)


def _check_has_labels_requirement(path: pathlib.Path) -> bool:
    with open(path, "r") as stream:
        lines = stream.readlines()
    for line in lines:
        requirement = _get_package_name(line)
        if requirement == "labels":
            return True
    return False


def _get_requirement_files() -> List[pathlib.Path]:
    return [
        *pathlib.Path(".").glob("**/requirements*.in"),
        *pathlib.Path(".").glob("**/requirements*.txt"),
        *pathlib.Path(".").glob("setup.cfg"),
    ]


def _get_package_name(line: str) -> str:
    package_name = line.split("#")[0]  # remove comment
    package_name = package_name.strip()
    package_name = package_name.split("<")[0]
    package_name = package_name.split(">")[0]
    package_name = package_name.split("=")[0]
    package_name = package_name.split("!")[0]
    return package_name.strip()


def _remove_all_labels_requirement() -> None:
    for file in _get_requirement_files():
        _remove_labels_requirement(file)


def _remove_labels_requirement(path: pathlib.Path) -> None:
    with open(path, "r") as stream:
        original_lines = stream.readlines()
    with open(path, "w") as stream:
        for line in original_lines:
            requirement = line
            requirement = requirement.split("<")[0]
            requirement = requirement.split(">")[0]
            requirement = requirement.split("=")[0]
            requirement = requirement.split("!")[0]
            requirement = requirement.strip()
            if requirement != "labels":
                stream.write(line)
