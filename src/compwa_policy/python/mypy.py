"""Check and update :code:`mypy` settings."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import rtoml
from ini2toml.api import Translator
from ruamel.yaml.comments import CommentedSeq

from compwa_policy.utilities import CONFIG_PATH, remove_lines, vscode
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    use_modifiable_pyproject,
)
from compwa_policy.utilities.readme import add_badge, remove_badge

if TYPE_CHECKING:
    from compwa_policy.utilities.changelog import Changelog
    from compwa_policy.utilities.precommit import ModifiablePrecommit


def main(
    active: bool,
    precommit: ModifiablePrecommit,
    pyproject: ModifiablePyproject | None = None,
) -> Changelog:
    changes: Changelog = []
    changes += _update_vscode_settings(active)
    with use_modifiable_pyproject(pyproject) as (config, include_changelog):
        if config is None:
            return changes
        if active:
            config.add_dependency("mypy", dependency_group=["style", "dev"])
            _merge_mypy_into_pyproject(config)
            _update_precommit_config(precommit)
            changes += remove_badge(r"http://(www\.)?mypy\-lang\.org/")
            changes += add_badge(
                "[![Type-checked with mypy](https://mypy-lang.org/static/mypy_badge.svg)](https://mypy.readthedocs.io)",
            )
        else:
            changes += _remove_mypy(precommit, config)
            changes += remove_lines(CONFIG_PATH.gitignore, ".*mypy.*")
        if include_changelog:
            changes += config.changelog
    return changes


def _merge_mypy_into_pyproject(pyproject: ModifiablePyproject) -> None:
    old_config_path = ".mypy.ini"
    if not os.path.exists(old_config_path):
        return
    with open(old_config_path) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name=old_config_path)
    mypy_config = rtoml.loads(toml_str)
    tool_table = pyproject.get_table("tool", create=True)
    tool_table.update(mypy_config)
    os.remove(old_config_path)
    msg = f"Imported mypy configuration from {old_config_path}"
    pyproject.changelog.append(msg)


def _remove_mypy(
    precommit: ModifiablePrecommit, pyproject: ModifiablePyproject
) -> Changelog:
    if pyproject.has_table("tool.mypy"):
        del pyproject._document["tool"]["mypy"]  # noqa: SLF001
        pyproject.changelog.append("Removed mypy configuration table")
    pyproject.remove_dependency("mypy")
    precommit.remove_hook("mypy")
    return remove_badge(r"\[\!\[.*[Mm]ypy.*\]\(.*mypy.*\)\]\(.*mypy.*\)\n?")


def _update_precommit_config(precommit: ModifiablePrecommit) -> None:
    types = CommentedSeq(["python"])
    types.fa.set_flow_style()
    hook = Hook(
        id="mypy",
        name="mypy",
        entry="mypy",
        language="system",
        require_serial=True,
        types=types,
    )
    expected_repo = Repo(repo="local", hooks=[hook])
    precommit.update_single_hook_repo(expected_repo)


def _update_vscode_settings(mypy: bool) -> Changelog:
    changes: Changelog = []
    if mypy:
        changes += vscode.add_extension_recommendation("ms-python.mypy-type-checker")
        settings = {
            "mypy-type-checker.args": [
                f"--config-file=${{workspaceFolder}}/{CONFIG_PATH.pyproject}"
            ],
        }
        changes += vscode.update_settings(settings)
    else:
        changes += vscode.remove_extension_recommendation(
            "ms-python.mypy-type-checker",
            unwanted=True,
        )
        changes += vscode.remove_settings(
            ["mypy-type-checker.args", "mypy-type-checker.importStrategy"],
        )
    return changes
