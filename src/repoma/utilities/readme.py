"""Helper functions for modifying :file:`README.md`."""

import os.path
import re

from repoma.errors import PrecommitError

__README_PATH = "README.md"


def add_badge(badge: str) -> None:  # noqa: R701
    if not os.path.exists(__README_PATH):
        msg = f"This repository contains no {__README_PATH}, so cannot add badge"
        raise PrecommitError(msg)
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
        if len(lines) == 0 or insert_position == len(lines) - 1:
            error_message += f"{__README_PATH} contains no title, so cannot add badge"
            raise PrecommitError(error_message)
        lines.insert(insert_position + 1, f"\n{badge}")
        with open(__README_PATH, "w") as stream:
            stream.writelines(lines)
        error_message += "Problem has been fixed."
        raise PrecommitError(error_message)


def remove_badge(badge_pattern: str) -> None:
    if not os.path.exists(__README_PATH):
        msg = f"This repository contains no {__README_PATH}, so cannot add badge"
        raise PrecommitError(msg)
    with open(__README_PATH) as stream:
        lines = stream.readlines()
    badge_line = None
    for line in lines:
        if re.match(badge_pattern, line):
            badge_line = line
            break
    if badge_line is None:
        return
    lines.remove(badge_line)
    with open(__README_PATH, "w") as stream:
        stream.writelines(lines)
    msg = f"A badge has been removed from {__README_PATH}:\n\n  {badge_line}"
    raise PrecommitError(msg)
