"""Check :file:`commitlint.config.js` config file."""
import os
from typing import Any, Dict

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, update_file
from repoma.utilities.yaml import create_prettier_round_trip_yaml


def main(repo_name: str, repo_title: str) -> None:
    update_file(CONFIG_PATH.release_drafter_workflow)
    _update_draft(repo_name, repo_title)


def _update_draft(repo_name: str, repo_title: str) -> None:
    yaml = create_prettier_round_trip_yaml()
    expected = _get_expected_config(repo_name, repo_title)
    output_path = CONFIG_PATH.release_drafter_config
    if not os.path.exists(output_path):
        yaml.dump(expected, output_path)
        raise PrecommitError(f"Created {output_path}")
    existing = _get_existing_config()
    if existing != expected:
        yaml.dump(expected, output_path)
        raise PrecommitError(f"Updated {output_path}")


def _get_expected_config(repo_name: str, repo_title: str) -> Dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(REPOMA_DIR / CONFIG_PATH.release_drafter_config)
    key = "name-template"
    config[key] = config[key].replace("<<REPO_TITLE>>", repo_title)
    key = "template"
    if os.path.exists(CONFIG_PATH.readthedocs):
        config[key] = config[key].replace("<<REPO_NAME>>", repo_name)
    else:
        config[key] = "$CHANGES"
    return config


def _get_existing_config() -> Dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    return yaml.load(CONFIG_PATH.release_drafter_config)
