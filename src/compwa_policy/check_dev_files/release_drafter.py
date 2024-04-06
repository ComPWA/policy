"""Update Release Drafter Action."""

from __future__ import annotations

import os
from typing import Any

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, update_file
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml


def main(
    repo_name: str, repo_title: str, github_pages: bool, organization: str
) -> None:
    update_file(CONFIG_PATH.release_drafter_workflow)
    _update_draft(repo_name, repo_title, github_pages, organization)


def _update_draft(
    repo_name: str, repo_title: str, github_pages: bool, organization: str
) -> None:
    yaml = create_prettier_round_trip_yaml()
    expected = _get_expected_config(repo_name, repo_title, github_pages, organization)
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


def _get_expected_config(
    repo_name: str, repo_title: str, github_pages: bool, organization: str
) -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(COMPWA_POLICY_DIR / CONFIG_PATH.release_drafter_config)
    key = "name-template"
    config[key] = config[key].replace("<<REPO_TITLE>>", repo_title)
    key = "template"
    lines = config[key].split("\n")
    if not os.path.exists(CONFIG_PATH.readthedocs) or github_pages:
        lines = lines[2:]
    config[key] = (
        "\n".join(lines)
        .replace("<<ORGANIZATION>>", organization)
        .replace("<<REPO_NAME>>", repo_name)
    )
    return config


def _get_existing_config() -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    return yaml.load(CONFIG_PATH.release_drafter_config)
