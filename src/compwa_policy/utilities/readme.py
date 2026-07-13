"""Helper functions for modifying :file:`README.md`."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from compwa_policy.errors import PolicyError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.resource import Changelog, ModifiableResource

if TYPE_CHECKING:
    from pathlib import Path

    from compwa_policy.utilities.session import Session

__README_PATH = str(CONFIG_PATH.readme)


class ModifiableReadme(ModifiableResource):
    """In-memory representation of :file:`README.md`."""

    def __init__(self, lines: list[str], source: Path, *, exists: bool) -> None:
        self._lines = lines
        self._source = source
        self._exists = exists
        self._changelog: Changelog = []

    @classmethod
    def load(cls, source: Path = CONFIG_PATH.readme) -> ModifiableReadme:
        if not source.exists():
            return cls([], source, exists=False)
        with source.open() as stream:
            return cls(stream.readlines(), source, exists=True)

    @property
    def changelog(self) -> Changelog:
        return self._changelog

    def dump(self) -> None:
        if not self._changelog:
            return
        with self._source.open("w") as stream:
            stream.writelines(self._lines)

    def add_badge(self, badge: str) -> None:
        if not self._exists:
            return
        stripped_lines = {line.strip("\n") for line in self._lines}
        stripped_lines = {line.strip("<br>") for line in stripped_lines}
        stripped_lines = {line.strip("<br />") for line in stripped_lines}
        if badge in stripped_lines:
            return
        error_message = f"{self._source} is missing a badge:\n  {badge}\n"
        if not self._lines:
            error_message += f"{self._source} contains no title, so cannot add badge"
            raise PolicyError(error_message)
        insert_position = 0
        for insert_position, line in enumerate(self._lines):  # noqa: B007
            if line.startswith("#"):
                break
        self._lines.insert(insert_position + 1, f"\n{badge}")
        self._changelog.append(error_message + "Problem has been fixed.")

    def remove_badge(self, badge_pattern: str) -> None:
        if not self._exists:
            return
        badge_line = next(
            (line for line in self._lines if re.match(badge_pattern, line)), None
        )
        if badge_line is None:
            return
        self._lines.remove(badge_line)
        self._changelog.append(
            f"A badge has been removed from {self._source}:\n\n  {badge_line}"
        )


def add_badge(session: Session, /, badge: str) -> Changelog:
    session.get(ModifiableReadme).add_badge(badge)
    return []


def remove_badge(session: Session, /, badge_pattern: str) -> Changelog:
    session.get(ModifiableReadme).remove_badge(badge_pattern)
    return []
