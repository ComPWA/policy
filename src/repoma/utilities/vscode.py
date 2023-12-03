"""Helper functions for modifying a VSCode configuration."""

from __future__ import annotations

import collections
import json
from collections import abc
from copy import deepcopy
from typing import TYPE_CHECKING, Iterable, OrderedDict, TypeVar, overload

from repoma.errors import PrecommitError
from repoma.utilities.executor import Executor

from . import CONFIG_PATH

if TYPE_CHECKING:
    from pathlib import Path


def remove_setting(key: str | dict) -> None:
    old = __load_config(CONFIG_PATH.vscode_settings, create=True)
    new = deepcopy(old)
    _recursive_remove_setting(key, new)
    _update_settings(old, new)


def _recursive_remove_setting(nested_keys: str | dict, settings: dict) -> None:
    if isinstance(nested_keys, str) and nested_keys in settings:
        settings.pop(nested_keys)
    elif isinstance(nested_keys, dict):
        for key, sub_keys in nested_keys.items():
            if key not in settings:
                continue
            if isinstance(sub_keys, str):
                sub_keys = [sub_keys]
            for sub_key in sub_keys:
                _recursive_remove_setting(sub_key, settings[key])


def remove_settings(keys: Iterable[str]) -> None:
    removed_keys = set(keys)
    settings = __load_config(CONFIG_PATH.vscode_settings, create=True)
    new_settings = {k: v for k, v in settings.items() if k not in removed_keys}
    _update_settings(settings, new=new_settings)


def set_setting(values: dict) -> None:
    settings = __load_config(CONFIG_PATH.vscode_settings, create=True)
    _update_settings(settings, new={**settings, **values})


def set_sub_setting(key: str, values: dict) -> None:
    settings = __load_config(CONFIG_PATH.vscode_settings, create=True)
    new_settings = dict(settings)
    new_settings[key] = {**settings.get(key, {}), **values}
    _update_settings(settings, new_settings)


def _update_settings(old: dict, new: dict) -> None:
    if old == new:
        return
    __dump_config(new, CONFIG_PATH.vscode_settings)
    msg = "Updated VS Code settings"
    raise PrecommitError(msg)


def add_extension_recommendation(extension_name: str) -> None:
    __add_extension(
        extension_name,
        key="recommendations",
        msg=f'Added VS Code extension recommendation "{extension_name}"',
    )


def add_unwanted_extension(extension_name: str) -> None:
    __add_extension(
        extension_name,
        key="unwantedRecommendations",
        msg=f'Added unwanted VS Code extension "{extension_name}"',
    )


def __add_extension(extension_name: str, key: str, msg: str) -> None:
    config = __load_config(CONFIG_PATH.vscode_extensions, create=True)
    recommended_extensions = config.get(key, [])
    if extension_name not in set(recommended_extensions):
        recommended_extensions.append(extension_name)
        config[key] = sorted(recommended_extensions)
        __dump_config(config, CONFIG_PATH.vscode_extensions)
        msg = f'Added VS Code extension recommendation "{extension_name}"'
        raise PrecommitError(msg)


def remove_extension_recommendation(
    extension_name: str, *, unwanted: bool = False
) -> None:
    def _remove() -> None:
        if not CONFIG_PATH.vscode_extensions.exists():
            return
        with open(CONFIG_PATH.vscode_extensions) as stream:
            config = json.load(stream)
        recommended_extensions = list(config.get("recommendations", []))
        if extension_name in recommended_extensions:
            recommended_extensions.remove(extension_name)
            config["recommendations"] = sorted(recommended_extensions)
            __dump_config(config, CONFIG_PATH.vscode_extensions)
            msg = f'Removed VS Code extension recommendation "{extension_name}"'
            raise PrecommitError(msg)

    executor = Executor()
    executor(_remove)
    if unwanted:
        executor(add_unwanted_extension, extension_name)
    executor.finalize()


def __dump_config(config: dict, path: Path) -> None:
    with open(path, "w") as stream:
        json.dump(sort_case_insensitive(config), stream, indent=2)
        stream.write("\n")


K = TypeVar("K")
V = TypeVar("V")


@overload
def sort_case_insensitive(dct: dict[K, V]) -> OrderedDict[K, V]: ...  # type: ignore[misc]
@overload
def sort_case_insensitive(dct: str) -> str: ...  # type: ignore[misc]
@overload
def sort_case_insensitive(dct: Iterable[K]) -> list[K]: ...  # type: ignore[misc]
@overload
def sort_case_insensitive(dct: K) -> K: ...
def sort_case_insensitive(dct):  # type: ignore[no-untyped-def]
    """Order a `dict` by key, **case-insensitive**.

    This function is implemented in order to :func:`~json.dump` a JSON file with a
    sorting that is the same as `the one used by VS Code
    <https://code.visualstudio.com/updates/v1_76#_jsonc-document-sorting>`_.

    >>> import pytest, sys
    >>> if sys.version_info >= (3, 12):
    ...     pytest.skip()
    ...
    >>> sort_case_insensitive(
    ...     {
    ...         "cSpell.enabled": True,
    ...         "coverage-gutters": ["test", "coverage.xml"],
    ...     }
    ... )
    OrderedDict([('coverage-gutters', ['coverage.xml', 'test']), ('cSpell.enabled', True)])
    """
    if isinstance(dct, abc.Mapping):
        return collections.OrderedDict(
            {k: sort_case_insensitive(dct[k]) for k in sorted(dct, key=str.lower)}
        )
    if isinstance(dct, str):
        return dct
    if isinstance(dct, abc.Iterable):
        return sorted(dct, key=lambda t: str(t).lower())
    return dct


def __load_config(path: Path, create: bool = False) -> dict:
    if not path.exists() and create:
        path.parent.mkdir(exist_ok=True)
        return {}
    with open(path) as stream:
        return json.load(stream)
