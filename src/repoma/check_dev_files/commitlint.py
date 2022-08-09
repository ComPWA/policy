"""Check :file:`commitlint.config.js` config file."""
import os
from shutil import copyfile

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR


def main() -> None:
    template_path = REPOMA_DIR / ".template" / CONFIG_PATH.commitlint
    if not os.path.exists(CONFIG_PATH.commitlint):
        copyfile(template_path, CONFIG_PATH.commitlint)
        raise PrecommitError(
            f"{CONFIG_PATH.commitlint} is missing, so created a new one. Please"
            " commit it."
        )
    with open(template_path) as f:
        expected_content = f.read()
    with open(CONFIG_PATH.commitlint) as f:
        existing_content = f.read()
    if expected_content != existing_content:
        copyfile(template_path, CONFIG_PATH.commitlint)
        raise PrecommitError(f"{CONFIG_PATH.commitlint} has been updated.")
