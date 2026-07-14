"""Update Release Drafter Action."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, update_file
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from pathlib import Path

    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Changelog, Session


@check_hook(
    group="github",
    paths=[CONFIG_PATH.readthedocs],
    directories=(CONFIG_PATH.github_workflow_dir.parent,),
    enabled=lambda args, ctx: ctx.is_python_repo and (not args.no_github_actions),
)
def check(session: Session, args: Arguments, _: CheckContext) -> None:
    if args.no_cd:
        paths_to_remove: list[Path] = [
            CONFIG_PATH.release_drafter_workflow,
            CONFIG_PATH.release_drafter_config,
        ]
        paths_to_remove = [p for p in paths_to_remove if p.is_file()]
        if paths_to_remove:
            for path in paths_to_remove:
                path.unlink()
            session.changelog.append(
                f"Removed {', '.join(str(p) for p in paths_to_remove)}"
            )
        return
    update_file(session, CONFIG_PATH.release_drafter_workflow)
    session.changelog += _update_draft(
        args.repo_name, args.repo_title, args.repo_organization
    )


def _update_draft(repo_name: str, repo_title: str, organization: str) -> Changelog:
    yaml = create_prettier_round_trip_yaml()
    expected = _get_expected_config(repo_name, repo_title, organization)
    output_path = CONFIG_PATH.release_drafter_config
    if not os.path.exists(output_path):
        yaml.dump(expected, output_path)
        return [f"Created {output_path}"]
    existing = _get_existing_config()
    if existing != expected:
        yaml.dump(expected, output_path)
        return [f"Updated {output_path}"]
    return []


def _get_expected_config(
    repo_name: str, repo_title: str, organization: str
) -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(COMPWA_POLICY_DIR / CONFIG_PATH.release_drafter_config)
    key = "name-template"
    config[key] = config[key].replace("<<REPO_TITLE>>", repo_title)
    key = "template"
    lines = config[key].split("\n")
    if not os.path.exists(CONFIG_PATH.readthedocs):
        lines = lines[2:]
    config[key] = (
        "\n"
        .join(lines)
        .replace("<<ORGANIZATION>>", organization)
        .replace("<<REPO_NAME>>", repo_name)
    )
    return config


def _get_existing_config() -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    return yaml.load(CONFIG_PATH.release_drafter_config)
