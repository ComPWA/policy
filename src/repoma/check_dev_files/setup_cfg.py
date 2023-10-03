"""Apply a certain set of standards to the :file:`setup.cfg`."""
# pyright: reportUnknownLambdaType=false
import dataclasses
import os
import re
import textwrap
from collections import defaultdict
from configparser import RawConfigParser
from typing import Dict, List, Tuple, Union

import tomlkit
from ini2toml.api import Translator
from tomlkit import TOMLDocument
from tomlkit.container import Container
from tomlkit.items import Array, Table

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.project_info import get_pypi_name
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
    extras_require = _get_recursive_optional_dependencies()
    if extras_require:
        _update_optional_dependencies(pyproject, extras_require)
    write_pyproject(pyproject)
    os.remove(setup_cfg)
    msg = f"Converted {setup_cfg} configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _get_recursive_optional_dependencies() -> Dict[str, List[Tuple[str, str]]]:
    if not CONFIG_PATH.setup_cfg.exists():
        return {}
    cfg = RawConfigParser()
    cfg.read(CONFIG_PATH.setup_cfg)
    section_name = "options.extras_require"
    if section_name not in cfg.sections():
        return {}
    return {
        option: __extract_package_list(cfg.get(section_name, option, raw=True))
        for option in cfg.options(section_name)
    }


def _update_optional_dependencies(
    pyproject: TOMLDocument, extras_require: Dict[str, List[Tuple[str, str]]]
) -> None:
    package_name = get_pypi_name(pyproject)
    optional_dependencies = tomlkit.table()
    for key, packages in extras_require.items():
        package_array = tomlkit.array()
        for package, comment in packages:
            package = re.sub(r"%\(([^\)]+)\)s", rf"{package_name}[\1]", package)
            toml_str = tomlkit.string(package, escape=False, literal='"' in package)
            package_array.append(toml_str)
            if comment:
                __add_comment(package_array, -1, comment)
        package_array.multiline(True)
        optional_dependencies[key] = package_array
    project = get_sub_table(pyproject, "project", create=True)
    project["optional-dependencies"] = optional_dependencies


def __extract_package_list(raw_content: str) -> List[Tuple[str, str]]:
    def split_comment(line: str) -> Tuple[str, str]:
        if "#" in line:
            return tuple(s.strip() for s in line.split("#", maxsplit=1))  # type: ignore[return-value]
        return line.strip(), ""

    raw_content = raw_content.strip()
    return [split_comment(s) for s in raw_content.split("\n")]


def __add_comment(array: Array, idx: int, comment: str) -> None:  # disgusting hack
    toml_comment = tomlkit.comment(comment)
    toml_comment.indent(1)
    toml_comment._trivia = dataclasses.replace(toml_comment._trivia, trail="")
    array._value[idx].comment = toml_comment


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
