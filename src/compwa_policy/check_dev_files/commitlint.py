"""Remove :file:`commitlint.config.js` config file.

See https://github.com/ComPWA/policy/issues/177.
"""

import os
from textwrap import dedent

from compwa_policy.errors import PrecommitError


def main() -> None:
    path = "commitlint.config.js"
    if not os.path.exists(path):
        return
    os.remove(path)
    msg = dedent(f"""
    Remove outdated {path}. Commitlint is now configured through
    https://github.com/ComPWA/commitlint-config.
    """).strip().replace("\n", " ")
    raise PrecommitError(msg)
