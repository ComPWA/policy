"""Check whether the repository (still) contains a ``labels.toml`` file.

If it's still there remove it, because it has been superceded by the
`github.com/ComPWA/meta <https://github.com/ComPWA/meta>`_ repository.
"""

import os
import pathlib
from typing import TYPE_CHECKING

from repoma._utilities import CONFIG_PATH
from repoma.errors import PrecommitError

if TYPE_CHECKING:
    from typing import List

__LABELS_CONFIG_FILE = "labels.toml"


def check_has_labels() -> None:
    if os.path.exists(__LABELS_CONFIG_FILE):
        os.remove(__LABELS_CONFIG_FILE)
        raise PrecommitError(
            f'Repository contains a file "{__LABELS_CONFIG_FILE}" for the'
            " labels package (see https://pypi.org/project/labels). This file"
            " should not be there, because labels are maintained through the"
            " https://github.com/ComPWA/meta repository. It has been removed."
        )
    faulty_req_files = [
        str(file.absolute())
        for file in _get_requirement_files()
        if _check_has_labels_requirement(file)
    ]
    if faulty_req_files:
        _remove_all_labels_requirement()
        raise PrecommitError(
            "Repository lists the labels package"
            " (https://pypi.org/project/labels) as a developer requirement."
            " Problems have been fixed, please re-stage files."
        )


def _check_has_labels_requirement(path: pathlib.Path) -> bool:
    with open(path) as stream:
        lines = stream.readlines()
    for line in lines:
        requirement = _get_package_name(line)
        if requirement == "labels":
            return True
    return False


def _get_requirement_files() -> "List[pathlib.Path]":
    return [
        *pathlib.Path(".").glob("**/requirements*.in"),
        *pathlib.Path(".").glob("**/requirements*.txt"),
        *pathlib.Path(".").glob(str(CONFIG_PATH.setup_cfg)),
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
    with open(path) as stream:
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
