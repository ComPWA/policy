"""Remove :file:`commitlint.config.js` config file.

See https://github.com/ComPWA/repo-maintenance/issues/177.
"""

import os

from repoma.errors import PrecommitError


def main() -> None:
    path = "commitlint.config.js"
    if not os.path.exists(path):
        return
    os.remove(path)
    msg = f"Remove outdated {path}"
    raise PrecommitError(msg)
