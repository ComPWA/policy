"""Check :file:`commitlint.config.js` config file."""
from repoma.utilities import CONFIG_PATH, update_file


def main() -> None:
    update_file(CONFIG_PATH.commitlint, in_template_folder=True)
