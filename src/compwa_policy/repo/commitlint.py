"""Remove :file:`commitlint.config.js` config file.

See https://github.com/ComPWA/policy/issues/177.
"""

from __future__ import annotations

import os
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from compwa_policy.utilities.changelog import Changelog


def main() -> Changelog:
    path = "commitlint.config.js"
    if not os.path.exists(path):
        return []
    os.remove(path)
    msg = f"""
    Remove outdated {path}. Commitlint is now configured through
    https://github.com/ComPWA/commitlint-config.
    """
    return [dedent(msg).strip().replace("\n", " ")]
