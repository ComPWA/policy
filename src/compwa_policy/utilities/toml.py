"""Helper functions for working with :mod:`tomlkit`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

import tomlkit

if TYPE_CHECKING:
    from tomlkit.items import Array


def to_toml_array(items: Iterable[Any], enforce_multiline: bool = False) -> Array:
    array = tomlkit.array()
    array.extend(items)
    if enforce_multiline or len(array) > 1:
        array.multiline(True)
    else:
        array.multiline(False)
    return array
