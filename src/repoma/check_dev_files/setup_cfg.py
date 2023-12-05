"""Apply a certain set of standards to the :file:`setup.cfg`."""

# pyright: reportUnknownLambdaType=false

from __future__ import annotations

import dataclasses
import os
import re
import textwrap
from collections import defaultdict
from configparser import RawConfigParser
from copy import deepcopy

import tomlkit
from ini2toml.api import Translator
from tomlkit import TOMLDocument
from tomlkit.container import Container
from tomlkit.items import Array, Table

from repoma.errors import PrecommitError
from repoma.format_setup_cfg import write_formatted_setup_cfg
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import remove_precommit_hook
from repoma.utilities.project_info import (
    ProjectInfo,
    get_project_info,
    get_pypi_name,
    get_supported_python_versions,
    open_setup_cfg,
)
from repoma.utilities.pyproject import (
    get_sub_table,
    load_pyproject,
    write_pyproject,
)


def main(ignore_author: bool) -> None:
    if CONFIG_PATH.setup_cfg.exists():
        _convert_to_pyproject()
    executor = Executor()
    executor(_check_required_options)
    if not ignore_author:
        executor(_update_author_data)
    executor(_fix_long_description)
    if CONFIG_PATH.pyproject.exists():
        executor(_remove_empty_tables)
    executor.finalize()


def _convert_to_pyproject() -> None:
    if "3.6" in get_supported_python_versions():
        return
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
    if os.path.exists("setup.py"):
        os.remove("setup.py")
    remove_precommit_hook("format-setup-cfg")
    msg = f"Converted {setup_cfg} configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _get_recursive_optional_dependencies() -> dict[str, list[tuple[str, str]]]:
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
    pyproject: TOMLDocument, extras_require: dict[str, list[tuple[str, str]]]
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


def __extract_package_list(raw_content: str) -> list[tuple[str, str]]:
    def split_comment(line: str) -> tuple[str, str]:
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


def _update_container(old: Container | Table, new: Container | Table) -> None:
    for key, value in new.items():
        if isinstance(value, (Container, Table)):
            if key in old:
                _update_container(old[key], value)  # type: ignore[arg-type]
            else:
                old[key] = value
        else:
            old[key] = value


def _check_required_options() -> None:
    if not has_pyproject_build_system():
        return
    pyproject = load_pyproject()
    project_info = get_project_info()
    if project_info.is_empty():
        return
    required_options = {
        "project": [
            "classifiers",
            "description",
            "license",
            "name",
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
            for option in sorted(options):
                summary += f"{option} = ...\n"
            summary += "...\n"
        raise PrecommitError(
            f"{CONFIG_PATH.pyproject} is missing the following options:\n"
            + textwrap.indent(summary, prefix="  ")
        )


def _update_author_data() -> None:
    __update_author_data_in_pyproject()
    __update_author_data_in_setup_cfg()


def __update_author_data_in_pyproject() -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    if not has_pyproject_build_system():
        return
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


def __update_author_data_in_setup_cfg() -> None:
    if not CONFIG_PATH.setup_cfg.exists():
        return
    old_cfg = open_setup_cfg()
    new_cfg = deepcopy(old_cfg)
    new_cfg.set("metadata", "author", "Common Partial Wave Analysis")
    new_cfg.set("metadata", "author_email", "Common Partial Wave Analysis")
    new_cfg.set("metadata", "author_email", "compwa-admin@ep1.rub.de")
    if new_cfg != old_cfg:
        write_formatted_setup_cfg(new_cfg)
        msg = f"Updated author info in ./{CONFIG_PATH.setup_cfg}"
        raise PrecommitError(msg)


def _fix_long_description() -> None:
    if not os.path.exists("README.md"):
        return
    __fix_long_description_in_pyproject()
    __fix_long_description_in_setup_cfg()


def __fix_long_description_in_pyproject() -> None:
    if not has_pyproject_build_system():
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
    project["readme"] = expected_readme
    write_pyproject(cfg)
    msg = f"Updated long_description in ./{CONFIG_PATH.setup_cfg}"
    raise PrecommitError(msg)


def __fix_long_description_in_setup_cfg() -> None:
    if not has_setup_cfg_build_system():
        return
    old_cfg = open_setup_cfg()
    new_cfg = deepcopy(old_cfg)
    new_cfg.set("metadata", "long_description", "file: README.md")
    new_cfg.set("metadata", "long_description_content_type", "text/markdown")
    if new_cfg != old_cfg:
        write_formatted_setup_cfg(new_cfg)
        msg = f"Updated long_description in ./{CONFIG_PATH.setup_cfg}"
        raise PrecommitError(msg)


def _remove_empty_tables() -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    pyproject = load_pyproject()
    if __recursive_remove_empty_tables(pyproject):
        write_pyproject(pyproject)
        msg = f"Removed empty tables from {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def __recursive_remove_empty_tables(table: Container | Table) -> bool:
    updated = False
    items = list(table.items())
    for key, value in items:
        if not isinstance(value, Table):
            continue
        if len(value) == 0:
            del table[key]
            updated = True
        else:
            updated |= __recursive_remove_empty_tables(value)
    return updated


def has_pyproject_build_system() -> bool:
    if not CONFIG_PATH.pyproject.exists():
        return False
    pyproject = load_pyproject()
    project_info = ProjectInfo.from_pyproject_toml(pyproject)
    return not project_info.is_empty()


def has_setup_cfg_build_system() -> bool:
    if not CONFIG_PATH.setup_cfg.exists():
        return False
    cfg = open_setup_cfg()
    return cfg.has_section("metadata")
