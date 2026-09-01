"""Update Release Drafter Action."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, select_autoescape
from ruamel.yaml.scalarstring import LiteralScalarString, PlainScalarString

from compwa_policy.github.workflows import copy_workflow_file
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
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
    copy_workflow_file(session, filename="release-drafter.yml")
    session.changelog += _update_draft(
        args.repo_name,
        args.repo_title,
        args.repo_organization,
        args.release_name_template,
        args.tag_prefix,
    )


def _update_draft(
    repo_name: str,
    repo_title: str,
    organization: str,
    release_name_template: str,
    tag_prefix: str,
) -> Changelog:
    yaml = create_prettier_round_trip_yaml()
    expected = _get_expected_config(
        repo_name, repo_title, organization, release_name_template, tag_prefix
    )
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
    repo_name: str,
    repo_title: str,
    organization: str,
    release_name_template: str,
    tag_prefix: str,
) -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    template_path = COMPWA_POLICY_DIR / f"{CONFIG_PATH.release_drafter_config}.jinja"
    config = yaml.load(template_path)
    environment = Environment(
        autoescape=select_autoescape(default_for_string=False),
        keep_trailing_newline=True,
    )
    context = {
        "HAS_READTHEDOCS": CONFIG_PATH.readthedocs.exists(),
        "ORGANIZATION": organization,
        "REPO_NAME": repo_name,
        "REPO_TITLE": repo_title,
        "TAG_PREFIX": tag_prefix,
    }
    config["name-template"] = PlainScalarString(
        environment.from_string(release_name_template).render(context)
    )
    config["tag-template"] = PlainScalarString(
        environment.from_string(config["tag-template"]).render(context)
    )
    config["template"] = LiteralScalarString(
        environment.from_string(config["template"]).render(context)
    )
    return config


def _get_existing_config() -> dict[str, Any]:
    yaml = create_prettier_round_trip_yaml()
    return yaml.load(CONFIG_PATH.release_drafter_config)
