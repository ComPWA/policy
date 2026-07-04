"""Types for user-facing policy change messages."""

from __future__ import annotations

from typing import TypeAlias

ChangelogItem: TypeAlias = str
"""A user-facing message that describes one policy change."""

Changelog: TypeAlias = list[ChangelogItem]
"""Messages reported by a policy check."""
