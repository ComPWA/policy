"""Update Release Drafter Action."""

from __future__ import annotations

import os
from typing import Any

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
        msg = f"Created {output_path}"
        raise PrecommitError(msg)
    existing = _get_existing_config()
    if existing != expected:
        yaml.dump(expected, output_path)
        msg = f"Updated {output_path}"
        raise PrecommitError(msg)


def _get_expected_config(repo_name: str, repo_title: str) -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(REPOMA_DIR / CONFIG_PATH.release_drafter_config)
    key = "name-template"
    config[key] = config[key].replace("<<REPO_TITLE>>", repo_title)
    key = "template"
    lines = config[key].split("\n")
    if not os.path.exists(CONFIG_PATH.readthedocs):
        lines = lines[2:]
    config[key] = "\n".join(lines).replace("<<REPO_NAME>>", repo_name)
    return config


def _get_existing_config() -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    return yaml.load(CONFIG_PATH.release_drafter_config)
