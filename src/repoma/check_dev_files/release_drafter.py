"""Check :file:`commitlint.config.js` config file."""
from repoma.utilities import CONFIG_PATH, update_file


def main() -> None:
    update_file(CONFIG_PATH.release_drafter_config)
    update_file(CONFIG_PATH.release_drafter_workflow)
