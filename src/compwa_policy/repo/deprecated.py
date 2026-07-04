"""Remove deprecated linters and formatters."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from compwa_policy.errors import PolicyError
from compwa_policy.utilities import CONFIG_PATH, remove_configs, remove_lines, vscode

if TYPE_CHECKING:
    from compwa_policy.utilities.changelog import Changelog
    from compwa_policy.utilities.precommit import ModifiablePrecommit


def remove_deprecated_tools(
    precommit: ModifiablePrecommit, keep_issue_templates: bool
) -> Changelog:
    changes: Changelog = []
    if not keep_issue_templates:
        changes += _remove_github_issue_templates()
    changes += _remove_markdownlint(precommit)
    for directory in ["docs", "doc"]:
        _remove_relink_references(directory)
    return changes


def _remove_github_issue_templates() -> Changelog:
    return remove_configs([
        ".github/ISSUE_TEMPLATE",
        ".github/pull_request_template.md",
    ])


def _remove_markdownlint(precommit: ModifiablePrecommit) -> Changelog:
    changes: Changelog = []
    changes += remove_configs([".markdownlint.json", ".markdownlint.yaml"])
    changes += remove_lines(CONFIG_PATH.gitignore, r"\.markdownlint\.json")
    changes += vscode.remove_extension_recommendation(
        # cspell:ignore davidanson markdownlint
        extension_name="davidanson.vscode-markdownlint",
        unwanted=True,
    )
    precommit.remove_hook("markdownlint")
    return changes


def _remove_relink_references(directory: str) -> None:
    path = f"{directory}/_relink_references.py"
    if not os.path.exists(path):
        return
    msg = (
        f"Please remove {path!r} and use https://pypi.org/project/sphinx-api-relink"
        " instead."
    )
    raise PolicyError(msg)
