"""Helper functions for working with :mod:`tomlkit`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

import tomlkit

if TYPE_CHECKING:
    from tomlkit.items import Array


def to_toml_array(items: Iterable[Any], multiline: bool | None = None) -> Array:
    array = tomlkit.array()
    array.extend(items)
    if multiline is None:
        array.multiline(len(array) > 1)
    else:
        array.multiline(multiline)
    return array
