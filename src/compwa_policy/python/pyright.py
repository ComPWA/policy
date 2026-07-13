"""Check and update :code:`pyright` settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, remove_lines, vscode
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import ModifiablePyproject, complies_with_subset
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.session import Changelog, Session


def main(session: Session, active: bool) -> None:
    session.changelog += _update_vscode_settings(active, session=session)
    config = session.pyproject
    if config is None:
        return
    if active:
        _merge_config_into_pyproject(config)
        _update_precommit(session.precommit)
        _remove_excludes(config)
        _update_settings(config)
    else:
        session.changelog += _remove_pyright(session=session)


def _merge_config_into_pyproject(
    pyproject: ModifiablePyproject,
    path: Path = Path("pyrightconfig.json"),
    remove: bool = True,
) -> None:
    old_config_path = path
    if not os.path.exists(old_config_path):
        return
    with open(old_config_path) as stream:
        existing_config = json.load(stream)
    for key, value in existing_config.items():
        if isinstance(value, list):
            existing_config[key] = to_toml_array(sorted(value))
    tool_table = pyproject.get_table("tool.pyright", create=True)
    tool_table.update(existing_config)
    if remove:
        os.remove(old_config_path)
    msg = f"Imported pyright configuration from {old_config_path}"
    pyproject.changelog.append(msg)


def _update_precommit(precommit: ModifiablePrecommit) -> None:
    old_url = "https://github.com/ComPWA/mirrors-pyright"
    old_repo = precommit.find_repo(old_url)
    rev = ""
    if old_repo is not None:
        precommit.remove_hook("pyright", old_url)
        rev = old_repo["rev"]
    repo = Repo(
        repo="https://github.com/ComPWA/pyright-pre-commit",
        rev=rev,
        hooks=[Hook(id="pyright")],
    )
    precommit.update_single_hook_repo(repo)


def _remove_excludes(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("tool.pyright"):
        return
    pyright_settings = pyproject.get_table("tool.pyright")
    if "exclude" not in pyright_settings:
        return
    del pyright_settings["exclude"]
    msg = "Removed pyright excludes"
    pyproject.changelog.append(msg)


def _update_settings(pyproject: ModifiablePyproject) -> None:
    pyright_settings = pyproject.get_table("tool.pyright", create=True)
    minimal_settings = dict(
        typeCheckingMode="strict",
        venv=".venv",
        venvPath=".",
    )
    if not complies_with_subset(pyright_settings, minimal_settings):
        pyright_settings.update(minimal_settings)
        msg = "Updated pyright configuration"
        pyproject.changelog.append(msg)


def _update_vscode_settings(
    active: bool,
    *,
    session: Session,
) -> Changelog:
    changes: Changelog = []
    if active:
        changes += vscode.add_extension_recommendation(
            "ms-python.vscode-pylance", session=session
        )
        changes += vscode.update_settings(
            {
                "python.analysis.autoImportCompletions": False,
                "python.analysis.inlayHints.pytestParameters": True,
            },
            session=session,
        )
    else:
        changes += vscode.remove_settings(
            [
                "python.analysis.autoImportCompletions",
                "python.analysis.inlayHints.pytestParameters",
            ],
            session=session,
        )
        changes += vscode.remove_extension_recommendation(
            "ms-python.vscode-pylance",
            unwanted=True,
            session=session,
        )
    return changes


def _remove_pyright(*, session: Session) -> Changelog:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return []
    pyright_config = Path("pyrightconfig.json")
    if pyright_config.exists():
        os.remove(pyright_config)
        msg = f"Removed old pyright configuration file {pyright_config}"
        pyproject.changelog.append(msg)
    if pyproject.has_table("tool.pyright"):
        del pyproject._document["tool"]["pyright"]  # noqa: SLF001
        msg = "Removed pyright configuration from pyproject.toml"
        pyproject.changelog.append(msg)
    pyproject.remove_dependency("pyright")
    precommit.remove_hook("pyright")
    return remove_lines(CONFIG_PATH.gitignore, ".*pyrightconfig.json", session=session)
