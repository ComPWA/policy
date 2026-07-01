"""Remove :file:`commitlint.config.js` config file.

See https://github.com/ComPWA/policy/issues/177.
"""

import os
from textwrap import dedent


def main() -> list[str]:
    path = "commitlint.config.js"
    if not os.path.exists(path):
        return []
    os.remove(path)
    msg = f"""
    Remove outdated {path}. Commitlint is now configured through
    https://github.com/ComPWA/commitlint-config.
    """
    return [dedent(msg).strip().replace("\n", " ")]
