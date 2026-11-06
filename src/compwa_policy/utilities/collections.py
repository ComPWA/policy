"""Explicit collection types that exclude bare strings and iterators."""

from typing import TypeAlias, TypeVar

T = TypeVar("T")

OrderedCollection: TypeAlias = list[T] | tuple[T, ...]
"""Ordered containers that exclude bare strings, unlike ``Sequence``."""

ExplicitCollection: TypeAlias = OrderedCollection[T] | set[T] | frozenset[T]
"""Concrete containers that exclude bare strings, unlike ``Collection``."""
