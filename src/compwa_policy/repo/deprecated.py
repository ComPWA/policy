"""Remove deprecated linters and formatters."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from compwa_policy.errors import PolicyError
from compwa_policy.utilities import CONFIG_PATH, remove_configs, remove_lines, vscode

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Session


def remove_deprecated_tools(session: Session, keep_issue_templates: bool) -> None:
    if not keep_issue_templates:
        _remove_github_issue_templates(session)
    _remove_markdownlint(session)
    for directory in ["docs", "doc"]:
        _remove_relink_references(directory)


def _remove_github_issue_templates(session: Session, /) -> None:
    remove_configs(
        session,
        [
            ".github/ISSUE_TEMPLATE",
            ".github/pull_request_template.md",
        ],
    )


def _remove_markdownlint(session: Session, /) -> None:
    remove_configs(session, [".markdownlint.json", ".markdownlint.yaml"])
    remove_lines(session, CONFIG_PATH.gitignore, r"\.markdownlint\.json")
    vscode.remove_extension_recommendation(
        session,  # cspell:ignore davidanson markdownlint
        extension_name="davidanson.vscode-markdownlint",
        unwanted=True,
    )
    session.precommit.remove_hook("markdownlint")


def _remove_relink_references(directory: str) -> None:
    path = f"{directory}/_relink_references.py"
    if not os.path.exists(path):
        return
    msg = (
        f"Please remove {path!r} and use https://pypi.org/project/sphinx-api-relink"
        " instead."
    )
    raise PolicyError(msg)
