"""Check configuration of VS Code."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.python import has_constraint_files

if TYPE_CHECKING:
    from compwa_policy.env.conda import PackageManagerChoice
    from compwa_policy.utilities.session import Changelog, Session


def main(
    session: Session,
    has_notebooks: bool,
    is_python_repo: bool,
    package_manager: PackageManagerChoice,
) -> None:
    session.changelog += _update_extensions(session=session)
    session.changelog += _update_settings(
        has_notebooks, is_python_repo, package_manager, session=session
    )


def _update_extensions(*, session: Session) -> Changelog:
    changes = vscode.add_extension_recommendation(
        "eamodio.gitlens", session=session
    )  # cspell:ignore eamodio
    changes += vscode.add_extension_recommendation(
        "mhutchie.git-graph", session=session
    )  # cspell:ignore mhutchie
    changes += vscode.add_extension_recommendation(
        "soulcode.vscode-unwanted-extensions", session=session
    )  # cspell:ignore Soulcode
    changes += vscode.add_extension_recommendation(
        "stkb.rewrap", session=session
    )  # cspell:ignore stkb
    changes += vscode.remove_extension_recommendation(
        "garaioag.garaio-vscode-unwanted-recommendations",  # cspell:ignore garaio garaioag
        unwanted=True,
        session=session,
    )
    changes += vscode.remove_extension_recommendation(
        "travisillig.vscode-json-stable-stringify",  # cspell:ignore travisillig
        unwanted=True,
        session=session,
    )
    changes += vscode.remove_extension_recommendation(
        "tyriar.sort-lines",  # cspell:ignore tyriar
        unwanted=True,
        session=session,
    )
    return changes


def _update_settings(
    has_notebooks: bool,
    is_python_repo: bool,
    package_manager: PackageManagerChoice,
    *,
    session: Session,
) -> Changelog:
    changes = vscode.update_settings(
        {
            "diffEditor.experimental.showMoves": True,
            "editor.formatOnSave": True,
            "gitlens.telemetry.enabled": False,
            "multiDiffEditor.experimental.enabled": True,
            "redhat.telemetry.enabled": False,
            "telemetry.telemetryLevel": "off",
        },
        session=session,
    )
    changes += vscode.update_settings(
        {
            "[git-commit]": {
                "editor.rulers": [72],
                "rewrap.wrappingColumn": 72,
            },
            "[json]": {
                "editor.wordWrap": "on",
            },
        },
        session=session,
    )
    changes += _remove_outdated_settings(session=session)
    changes += _update_doc_settings(session=session)
    if has_notebooks:
        changes += _update_notebook_settings(session=session)
    changes += _update_pytest_settings(session=session)
    if has_constraint_files():
        changes += vscode.update_settings(
            {"files.associations": {"**/.constraints/py*.txt": "pip-requirements"}},
            session=session,
        )
    if is_python_repo:
        if package_manager == "pixi":
            python_path = ".pixi/envs/default/bin/python"
        else:
            python_path = ".venv/bin/python"
        changes += vscode.update_settings(
            {
                "python.defaultInterpreterPath": python_path,
                "rewrap.wrappingColumn": 88,
            },
            session=session,
        )
        if CONFIG_PATH.envrc.exists():
            changes += vscode.update_settings(
                {"python.terminal.activateEnvironment": False}, session=session
            )
    return changes


def _remove_outdated_settings(*, session: Session) -> Changelog:
    outdated_settings = [
        "editor.rulers",
        "githubPullRequests.telemetry.enabled",
        "gitlens.advanced.telemetry.enabled",
        "python.analysis.diagnosticMode",
        "python.analysis.typeCheckingMode",
        "python.formatting.provider",
        "python.linting.banditEnabled",
        "python.linting.enabled",
        "python.linting.flake8Enabled",
        "python.linting.mypyEnabled",
        "python.linting.pydocstyleEnabled",
        "python.linting.pylamaEnabled",
        "python.linting.pylintEnabled",
        "telemetry.enableCrashReporter",
        "telemetry.enableTelemetry",
    ]
    return vscode.remove_settings(outdated_settings, session=session)


def _update_doc_settings(*, session: Session) -> Changelog:
    if not os.path.exists("docs/"):
        return []
    changes = vscode.update_settings(
        {"livePreview.defaultPreviewPath": "docs/_build/html"}, session=session
    )
    changes += vscode.add_extension_recommendation(
        "ms-vscode.live-server", session=session
    )
    # cspell:ignore executablebookproject
    myst_extension = "executablebookproject.myst-highlight"
    if myst_extension not in vscode.get_unwanted_extensions(session=session):
        changes += vscode.add_extension_recommendation(myst_extension, session=session)
    return changes


def _update_notebook_settings(*, session: Session) -> Changelog:
    """https://code.visualstudio.com/updates/v1_83#_go-to-symbol-in-notebooks."""
    if not os.path.exists("docs/"):
        return []
    return vscode.update_settings(
        {"notebook.gotoSymbols.showAllSymbols": True}, session=session
    )


def _update_pytest_settings(*, session: Session) -> Changelog:
    if not os.path.exists("tests/"):
        return []
    return vscode.update_settings(
        {
            "python.testing.pytestEnabled": True,
            "python.testing.unittestEnabled": False,
        },
        session=session,
    )
