"""Tools for loading, inspecting, and updating :code:`pyproject.toml`."""

from __future__ import annotations

import io
from collections import abc
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Iterable, Sequence

import tomlkit
from tomlkit.toml_document import TOMLDocument

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import find_repo, load_precommit_config

if TYPE_CHECKING:
    from tomlkit.container import Container
    from tomlkit.items import Array, Table


def add_dependency(  # noqa: C901, PLR0912
    package: str,
    optional_key: str | Sequence[str] | None = None,
    source: IO | (Path | (TOMLDocument | str)) = CONFIG_PATH.pyproject,
    target: IO | (Path | str) | None = None,
) -> None:
    if isinstance(source, TOMLDocument):
        pyproject = source
    else:
        pyproject = load_pyproject(source)
    if target is None:
        if isinstance(source, TOMLDocument):
            msg = "If the source is a TOML document, you have to specify a target"
            raise TypeError(msg)
        target = source
    if optional_key is None:
        project = get_sub_table(pyproject, "project", create=True)
        existing_dependencies: set[str] = set(project.get("dependencies", []))
        if package in existing_dependencies:
            return
        existing_dependencies.add(package)
        project["dependencies"] = to_toml_array(_sort_taplo(existing_dependencies))
    elif isinstance(optional_key, str):
        optional_dependencies = get_sub_table(
            pyproject, "project.optional-dependencies", create=True
        )
        existing_dependencies = set(optional_dependencies.get(optional_key, []))
        if package in existing_dependencies:
            return
        existing_dependencies.add(package)
        existing_dependencies = set(existing_dependencies)
        optional_dependencies[optional_key] = to_toml_array(
            _sort_taplo(existing_dependencies)
        )
    elif isinstance(optional_key, abc.Sequence):
        if len(optional_key) < 2:  # noqa: PLR2004
            msg = "Need at least two keys to define nested optional dependencies"
            raise ValueError(msg)
        this_package = get_package_name_safe(pyproject)
        executor = Executor()
        for key, previous in zip(optional_key, [None, *optional_key]):
            if previous is None:
                executor(add_dependency, package, key, source, target)
            else:
                executor(
                    add_dependency, f"{this_package}[{previous}]", key, source, target
                )
        if executor.finalize() == 0:
            return
    else:
        msg = f"Unsupported type for optional_key: {type(optional_key)}"
        raise NotImplementedError(msg)
    write_pyproject(pyproject, target)
    msg = f"Listed {package} as a dependency under {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _sort_taplo(items: Iterable[str]) -> list[str]:
    return sorted(items, key=lambda s: ('"' in s, s))


def complies_with_subset(settings: dict, minimal_settings: dict) -> bool:
    return all(settings.get(key) == value for key, value in minimal_settings.items())


def load_pyproject(source: IO | (Path | str) = CONFIG_PATH.pyproject) -> TOMLDocument:
    if isinstance(source, io.IOBase):
        source.seek(0)
        return tomlkit.load(source)
    if isinstance(source, Path):
        with open(source) as stream:
            return load_pyproject(stream)
    if isinstance(source, str):
        return tomlkit.loads(source)
    msg = f"Source of type {type(source).__name__} is not supported"
    raise TypeError(msg)


def get_package_name(
    source: IO | (Path | (TOMLDocument | str)) = CONFIG_PATH.pyproject,
) -> str | None:
    if isinstance(source, TOMLDocument):
        pyproject = source
    else:
        pyproject = load_pyproject(source)
    project = get_sub_table(pyproject, "project", create=True)
    package_name = project.get("name")
    if package_name is None:
        return None
    return package_name


def get_package_name_safe(
    source: IO | (Path | (TOMLDocument | str)) = CONFIG_PATH.pyproject,
) -> str:
    package_name = get_package_name(source)
    if package_name is None:
        msg = (
            "Please provide a name for the package under the [project] table in"
            f" {CONFIG_PATH.pyproject}"
        )
        raise PrecommitError(msg)
    return package_name


def get_sub_table(config: Container, dotted_header: str, create: bool = False) -> Table:
    """Get a TOML sub-table through a dotted header key."""
    current_table: Any = config
    for header in dotted_header.split("."):
        if header not in current_table:
            if create:
                current_table[header] = tomlkit.table()
            else:
                msg = f"TOML data does not contain {dotted_header!r}"
                raise KeyError(msg)
        current_table = current_table[header]
    return current_table


def write_pyproject(
    config: TOMLDocument, target: IO | (Path | str) = CONFIG_PATH.pyproject
) -> None:
    if isinstance(target, io.IOBase):
        target.seek(0)
        tomlkit.dump(config, target, sort_keys=True)
    elif isinstance(target, (Path, str)):
        src = tomlkit.dumps(config, sort_keys=True)
        src = f"{src.strip()}\n"
        with open(target, "w") as stream:
            stream.write(src)
    else:
        msg = f"Target of type {type(target).__name__} is not supported"
        raise TypeError(msg)


def to_toml_array(items: Iterable[Any], enforce_multiline: bool = False) -> Array:
    array = tomlkit.array()
    array.extend(items)
    if enforce_multiline or len(array) > 1:
        array.multiline(True)
    else:
        array.multiline(False)
    return array


def update_nbqa_settings(key: str, expected: Any) -> None:
    # cspell:ignore addopts
    if not CONFIG_PATH.precommit.exists():
        return
    if not __has_nbqa_precommit_repo():
        return
    pyproject = load_pyproject()
    nbqa_table = get_sub_table(pyproject, "tool.nbqa.addopts", create=True)
    if nbqa_table.get(key) != expected:
        nbqa_table[key] = expected
        write_pyproject(pyproject)
        msg = f"Added nbQA configuration for {key!r}"
        raise PrecommitError(msg)


def __has_nbqa_precommit_repo() -> bool:
    config = load_precommit_config()
    return find_repo(config, "https://github.com/nbQA-dev/nbQA") is not None
