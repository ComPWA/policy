"""Helper functions for modifying a VSCode configuration."""

from __future__ import annotations

import json
from collections import abc
from collections.abc import Iterable, Sized
from typing import TYPE_CHECKING, TypeVar, Union

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor

if TYPE_CHECKING:
    from pathlib import Path


K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")


RemovedKeys = Union[Iterable[str], dict[str, "RemovedKeys"]]
"""Type for keys to be removed from a (nested) dictionary."""


def get_unwanted_extensions() -> set[str]:
    config = __load_config(CONFIG_PATH.vscode_extensions)
    unwanted_extensions = config.get("unwantedRecommendations", set())
    return {ext.lower() for ext in unwanted_extensions}


def remove_settings(keys: RemovedKeys) -> None:
    settings = __load_config(CONFIG_PATH.vscode_settings, create=True)
    new_settings = _remove_keys(settings, keys)
    _update_settings_if_changed(settings, new=new_settings)


def _remove_keys(obj: T, keys: RemovedKeys) -> T:
    """Recursively remove keys from a (nested) dictionary.

    >>> dct = {"a": 1, "b": 2, "c": 3, "d": [4, 5], "sub_key": {"d": 6, "e": [7, 8]}}
    >>> _remove_keys(dct, {"a", "c"})
    {'b': 2, 'd': [4, 5], 'sub_key': {'d': 6, 'e': [7, 8]}}
    >>> _remove_keys(dct, {"sub_key": {"d"}})
    {'a': 1, 'b': 2, 'c': 3, 'd': [4, 5], 'sub_key': {'e': [7, 8]}}
    >>> _remove_keys(dct, {"sub_key": {"d", "e"}})
    {'a': 1, 'b': 2, 'c': 3, 'd': [4, 5]}
    >>> _remove_keys(dct, {"d": [5]})
    {'a': 1, 'b': 2, 'c': 3, 'd': [4], 'sub_key': {'d': 6, 'e': [7, 8]}}
    """
    if not keys:
        return obj
    if isinstance(obj, list):
        return [k for k in obj if k not in keys]  # type:ignore[return-value]
    if isinstance(obj, dict):
        if isinstance(keys, dict):
            new_dict = {}
            for key, value in obj.items():
                sub_keys_to_remove = keys.get(key, {})
                new_value = _remove_keys(value, sub_keys_to_remove)
                if (
                    isinstance(new_value, abc.Iterable)
                    and not isinstance(new_value, str)
                    and isinstance(new_value, Sized)
                    and len(new_value) == 0
                ):
                    continue
                new_dict[key] = _remove_keys(value, keys.get(key, {}))
            return new_dict  # type:ignore[return-value]
        if isinstance(keys, abc.Iterable) and not isinstance(keys, str):
            removed_keys = set(keys)
            return {k: v for k, v in obj.items() if k not in removed_keys}  # type:ignore[return-value]
        msg = f"Invalid type for removed keys: {type(keys)}"
        raise TypeError(msg)
    return obj


def update_settings(new_settings: dict) -> None:
    old = __load_config(CONFIG_PATH.vscode_settings, create=True)
    updated = _update_dict_recursively(old, new_settings)
    _update_settings_if_changed(old, updated)


def _update_dict_recursively(old: dict, new: dict, sort: bool = False) -> dict:
    """Update a `dict` recursively.

    >>> old = {
    ...     "k1": "old",
    ...     "k2": {"s1": "old", "s2": "old"},
    ...     "k5": [1, 2],
    ... }
    >>> new = {
    ...     "k1": "new",
    ...     "k2": {"s2": "new"},
    ...     "k3": {"s": "a"},
    ...     "k4": "b",
    ...     "k5": [1, 2, 3],
    ... }
    >>> _update_dict_recursively(old, new, sort=True)
    {'k1': 'new', 'k2': {'s1': 'old', 's2': 'new'}, 'k3': {'s': 'a'}, 'k4': 'b', 'k5': [1, 2, 3]}
    >>> old  # check if unchanged
    {'k1': 'old', 'k2': {'s1': 'old', 's2': 'old'}, 'k5': [1, 2]}
    """
    merged = dict(old)
    for key, value in new.items():
        if key in merged:
            merged[key] = _determine_new_value(merged[key], value, sort)
        else:
            merged[key] = value
    if sort:
        return {k: merged[k] for k in sorted(merged)}
    return merged


def _determine_new_value(old: V, new: V, sort: bool = False) -> V:
    if isinstance(old, dict) and isinstance(new, dict):
        return _update_dict_recursively(old, new, sort)  # type: ignore[return-value]
    if isinstance(old, list) and isinstance(new, list):
        return sorted({*old, *new})  # type: ignore[return-value]
    return new


def _update_settings_if_changed(old: dict, new: dict) -> None:
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
    recommended_extensions = __to_lower(config.get(key, []))
    extension_name = extension_name.lower()
    if extension_name not in set(recommended_extensions):
        recommended_extensions.append(extension_name)
        config[key] = sorted(recommended_extensions)
        __dump_config(config, CONFIG_PATH.vscode_extensions)
        msg = f'Added VS Code extension recommendation "{extension_name}"'
        raise PrecommitError(msg)


def remove_extension_recommendation(
    extension_name: str, *, unwanted: bool = False
) -> None:
    def _remove(extension_name: str) -> None:
        if not CONFIG_PATH.vscode_extensions.exists():
            return
        with open(CONFIG_PATH.vscode_extensions) as stream:
            config = json.load(stream)
        recommended_extensions = __to_lower(config.get("recommendations", []))
        extension_name = extension_name.lower()
        if extension_name in recommended_extensions:
            recommended_extensions.remove(extension_name)
            config["recommendations"] = sorted(recommended_extensions)
            __dump_config(config, CONFIG_PATH.vscode_extensions)
            msg = f'Removed VS Code extension recommendation "{extension_name}"'
            raise PrecommitError(msg)

    with Executor() as do:
        do(_remove, extension_name)
        if unwanted:
            do(add_unwanted_extension, extension_name)


def __to_lower(lst: list[str]) -> list[str]:
    return [e.lower() for e in lst]


def __dump_config(config: dict, path: Path) -> None:
    with open(path, "w") as stream:
        json.dump(config, stream, indent=2, sort_keys=True)
        stream.write("\n")


def __load_config(path: Path, create: bool = False) -> dict:
    if not path.exists() and create:
        path.parent.mkdir(exist_ok=True)
        return {}
    with open(path) as stream:
        return json.load(stream)
