"""Helper functions for modifying :file:`README.md`."""

from __future__ import annotations

import os.path
import re
from typing import TYPE_CHECKING

from compwa_policy.errors import PolicyError

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Changelog

__README_PATH = "README.md"


def add_badge(badge: str) -> Changelog:
    if not os.path.exists(__README_PATH):
        return []
    with open(__README_PATH) as stream:
        lines = stream.readlines()
    stripped_lines = {s.strip("\n") for s in lines}
    stripped_lines = {s.strip("<br>") for s in stripped_lines}
    stripped_lines = {s.strip("<br />") for s in stripped_lines}
    if badge not in stripped_lines:
        error_message = f"{__README_PATH} is missing a badge:\n"
        error_message += f"  {badge}\n"
        insert_position = 0
        for insert_position, line in enumerate(lines):  # noqa: B007
            if line.startswith("#"):  # find first Markdown section
                break
        if len(lines) == 0:
            error_message += f"{__README_PATH} contains no title, so cannot add badge"
            raise PolicyError(error_message)
        lines.insert(insert_position + 1, f"\n{badge}")
        with open(__README_PATH, "w") as stream:
            stream.writelines(lines)
        error_message += "Problem has been fixed."
        return [error_message]
    return []


def remove_badge(badge_pattern: str) -> Changelog:
    if not os.path.exists(__README_PATH):
        return []
    with open(__README_PATH) as stream:
        lines = stream.readlines()
    badge_line = None
    for line in lines:
        if re.match(badge_pattern, line):
            badge_line = line
            break
    if badge_line is None:
        return []
    lines.remove(badge_line)
    with open(__README_PATH, "w") as stream:
        stream.writelines(lines)
    return [f"A badge has been removed from {__README_PATH}:\n\n  {badge_line}"]
