"""Apply a certain set of standards to the :file:`setup.cfg`."""

import os
import textwrap
from collections import defaultdict
from typing import Union

import tomlkit
from ini2toml.api import Translator
from tomlkit.container import Container
from tomlkit.items import Table

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.pyproject import (
    get_sub_table,
    load_pyproject,
    write_pyproject,
)


def main(ignore_author: bool) -> None:
    if CONFIG_PATH.setup_cfg.exists():
        _convert_to_pyproject()
    if not CONFIG_PATH.pyproject.exists():
        return
    executor = Executor()
    executor(_check_required_options)
    if not ignore_author:
        executor(_update_author_data)
    executor(_fix_long_description)
    executor.finalize()


def _convert_to_pyproject() -> None:
    setup_cfg = CONFIG_PATH.setup_cfg
    with open(setup_cfg) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name=str(setup_cfg))
    converted_cfg = tomlkit.parse(toml_str)
    pyproject = load_pyproject()
    _update_container(pyproject, converted_cfg)
    write_pyproject(pyproject)
    os.remove(setup_cfg)
    msg = f"Converted {setup_cfg} configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _update_container(
    old: Union[Container, Table], new: Union[Container, Table]
) -> None:
    for key, value in new.items():
        if isinstance(value, (Container, Table)):
            if key in old:
                _update_container(old[key], value)  # type: ignore[arg-type]
            else:
                old[key] = value
        else:
            old[key] = value


def _check_required_options() -> None:
    pyproject = load_pyproject()
    required_options = {
        "project": [
            "name",
            "description",
            "license",
            "classifiers",
            "requires-python",
        ],
    }
    missing_options = defaultdict(list)
    for section, options in required_options.items():
        for option in options:
            if option in get_sub_table(pyproject, section, create=True):
                continue
            missing_options[section].append(option)
    if missing_options:
        summary = "\n"
        for section, options in missing_options.items():
            summary += f"[{section}]\n...\n"
            for option in options:
                summary += f"{option} = ...\n"
            summary += "...\n"
        raise PrecommitError(
            f"{CONFIG_PATH.pyproject} is missing the following options:\n"
            + textwrap.indent(summary, prefix="  ")
        )


def _update_author_data() -> None:
    pyproject = load_pyproject()
    author_info = dict(
        name="Common Partial Wave Analysis",
        email="compwa-admin@ep1.rub.de",
    )
    authors = tomlkit.array().multiline(True)
    authors.append(author_info)
    project = get_sub_table(pyproject, "project", create=True)
    if project.get("authors") != authors:
        pyproject["project"]["authors"] = authors  # type: ignore[index]
        write_pyproject(pyproject)
        msg = f"Updated author info in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def _fix_long_description() -> None:
    if not os.path.exists("README.md"):
        return
    cfg = load_pyproject()
    project = get_sub_table(cfg, "project", create=True)
    existing_readme = project.get("readme")
    expected_readme = {
        "content-type": "text/markdown",
        "file": "README.md",
    }
    if existing_readme == expected_readme:
        return
    project["readme "] = expected_readme
    write_pyproject(cfg)
    msg = f"Updated long_description in ./{CONFIG_PATH.setup_cfg}"
    raise PrecommitError(msg)
