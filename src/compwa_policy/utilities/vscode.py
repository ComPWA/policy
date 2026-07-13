"""Helper functions for modifying a VSCode configuration."""

from __future__ import annotations

import json
import sys
from collections import abc
from collections.abc import Iterable, Sized
from functools import cache
from typing import TYPE_CHECKING, Any, TypeVar

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.resource import Changelog, ModifiableResource

if TYPE_CHECKING:
    from pathlib import Path

    from compwa_policy.utilities.session import Session
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T", dict, list, Any)


RemovedKeys = Iterable[str] | dict[str, "RemovedKeys"]
"""Type for keys to be removed from a (nested) dictionary."""


class _ModifiableJsonResource(ModifiableResource):
    path: Path

    def __init__(self, document: dict, *, exists: bool) -> None:
        self._document = document
        self._exists = exists
        self._changelog: Changelog = []

    @classmethod
    def load(cls) -> Self:
        if not cls.path.exists():
            return cls({}, exists=False)
        with cls.path.open() as stream:
            return cls(json.load(stream), exists=True)

    @property
    def changelog(self) -> Changelog:
        return self._changelog

    def dump(self) -> None:
        if not self._changelog:
            return
        self.path.parent.mkdir(exist_ok=True)
        _dump_config(self._document, self.path)


class ModifiableVscodeSettings(_ModifiableJsonResource):
    """In-memory representation of :file:`.vscode/settings.json`."""

    path = CONFIG_PATH.vscode_settings

    def remove(self, keys: RemovedKeys) -> None:
        updated = _remove_keys(self._document, keys)
        if updated != self._document:
            self._document = updated
            self._changelog.append("Updated VS Code settings")

    def update(self, new_settings: dict) -> None:
        updated = _update_dict_recursively(self._document, new_settings)
        if updated != self._document:
            self._document = updated
            self._changelog.append("Updated VS Code settings")


class ModifiableVscodeExtensions(_ModifiableJsonResource):
    """In-memory representation of :file:`.vscode/extensions.json`."""

    path = CONFIG_PATH.vscode_extensions

    def get_recommended(self) -> set[str]:
        return self._get("recommendations")

    def get_unwanted(self) -> set[str]:
        return self._get("unwantedRecommendations")

    def add_recommendation(self, extension_name: str) -> None:
        self._add(extension_name, "recommendations")
        self._remove(extension_name, "unwantedRecommendations")

    def add_unwanted(self, extension_name: str) -> None:
        self._add(extension_name, "unwantedRecommendations")
        self._remove(extension_name, "recommendations")

    def remove_recommendation(
        self, extension_name: str, *, unwanted: bool = False
    ) -> None:
        self._remove(extension_name, "recommendations")
        if unwanted:
            self.add_unwanted(extension_name)

    def _get(self, key: str) -> set[str]:
        return set(_to_lower(self._document.get(key, [])))

    def _add(self, extension_name: str, key: str) -> None:
        extensions = _to_lower(self._document.get(key, []))
        extension_name = extension_name.lower()
        if extension_name in extensions:
            return
        extensions.append(extension_name)
        self._document[key] = sorted(extensions)
        self._changelog.append(
            f'Added VS Code extension recommendation "{extension_name}"'
        )

    def _remove(self, extension_name: str, key: str) -> None:
        if not self._exists:
            return
        extensions = _to_lower(self._document.get(key, []))
        extension_name = extension_name.lower()
        if extension_name not in extensions:
            return
        extensions.remove(extension_name)
        self._document[key] = sorted(extensions)
        self._changelog.append(
            f'Removed VS Code extension recommendation "{extension_name}"'
        )


def get_recommended_extensions(session: Session, /) -> set[str]:
    return session.get(ModifiableVscodeExtensions).get_recommended()


def get_unwanted_extensions(session: Session, /) -> set[str]:
    return session.get(ModifiableVscodeExtensions).get_unwanted()


@cache
def _get_extension_recommendations(key: str) -> set[str]:
    config = __load_config(CONFIG_PATH.vscode_extensions)
    extensions = config.get(key, set())
    return {ext.lower() for ext in extensions}


def remove_settings(session: Session, /, keys: RemovedKeys) -> Changelog:
    session.get(ModifiableVscodeSettings).remove(keys)
    return []


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
        return [k for k in obj if k not in keys]  # ty:ignore[invalid-return-type]
    if isinstance(obj, dict):
        if isinstance(keys, dict):
            new_dict = {}
            for key, value in obj.items():
                sub_keys_to_remove = keys.get(key, {})
                new_value = _remove_keys(value, sub_keys_to_remove)  # ty:ignore[invalid-argument-type]
                if (
                    isinstance(new_value, abc.Iterable)
                    and not isinstance(new_value, str)
                    and isinstance(new_value, Sized)
                    and len(new_value) == 0
                ):
                    continue
                new_dict[key] = _remove_keys(value, keys.get(key, {}))  # ty:ignore[invalid-argument-type]
            return new_dict  # ty:ignore[invalid-return-type]
        if isinstance(keys, abc.Iterable) and not isinstance(keys, str):
            removed_keys = set(keys)
            return {k: v for k, v in obj.items() if k not in removed_keys}  # ty:ignore[invalid-return-type]
        msg = f"Invalid type for removed keys: {type(keys)}"
        raise TypeError(msg)
    return obj


def update_settings(session: Session, /, new_settings: dict) -> Changelog:
    session.get(ModifiableVscodeSettings).update(new_settings)
    return []


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
        return _update_dict_recursively(old, new, sort)  # ty:ignore[invalid-return-type]
    if isinstance(old, list) and isinstance(new, list):
        return sorted({*old, *new})  # ty:ignore[invalid-return-type]
    return new


def _update_settings_if_changed(old: dict, new: dict) -> Changelog:
    if old == new:
        return []
    _dump_config(new, CONFIG_PATH.vscode_settings)
    return ["Updated VS Code settings"]


def add_extension_recommendation(session: Session, /, extension_name: str) -> Changelog:
    session.get(ModifiableVscodeExtensions).add_recommendation(extension_name)
    return []


def add_unwanted_extension(session: Session, /, extension_name: str) -> Changelog:
    session.get(ModifiableVscodeExtensions).add_unwanted(extension_name)
    return []


def __add_extension(extension_name: str, key: str) -> Changelog:
    config = __load_config(CONFIG_PATH.vscode_extensions, create=True)
    recommended_extensions = _to_lower(config.get(key, []))
    extension_name = extension_name.lower()
    if extension_name not in set(recommended_extensions):
        recommended_extensions.append(extension_name)
        config[key] = sorted(recommended_extensions)
        _dump_config(config, CONFIG_PATH.vscode_extensions)
        return [f'Added VS Code extension recommendation "{extension_name}"']
    return []


def __remove_extension(extension_name: str, key: str) -> Changelog:
    if not CONFIG_PATH.vscode_extensions.exists():
        return []
    with open(CONFIG_PATH.vscode_extensions) as stream:
        config = json.load(stream)
    recommended_extensions = _to_lower(config.get(key, []))
    extension_name = extension_name.lower()
    if extension_name in recommended_extensions:
        recommended_extensions.remove(extension_name)
        config[key] = sorted(recommended_extensions)
        _dump_config(config, CONFIG_PATH.vscode_extensions)
        return [f'Removed VS Code extension recommendation "{extension_name}"']
    return []


def remove_extension_recommendation(
    session: Session, /, extension_name: str, *, unwanted: bool = False
) -> Changelog:
    session.get(ModifiableVscodeExtensions).remove_recommendation(
        extension_name, unwanted=unwanted
    )
    return []


def _to_lower(lst: list[str]) -> list[str]:
    return [e.lower() for e in lst]


def _dump_config(config: dict, path: Path) -> None:
    with open(path, "w") as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def __load_config(path: Path, create: bool = False) -> dict:
    if not path.exists() and create:
        path.parent.mkdir(exist_ok=True)
        return {}
    with open(path) as stream:
        return json.load(stream)
