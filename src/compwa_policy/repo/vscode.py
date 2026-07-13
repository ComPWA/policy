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
    session.changelog += _update_extensions(session)
    session.changelog += _update_settings(
        session, has_notebooks, is_python_repo, package_manager
    )


def _update_extensions(session: Session, /) -> Changelog:
    changes = vscode.add_extension_recommendation(
        session, "eamodio.gitlens"
    )  # cspell:ignore eamodio
    changes += vscode.add_extension_recommendation(
        session, "mhutchie.git-graph"
    )  # cspell:ignore mhutchie
    changes += vscode.add_extension_recommendation(
        session, "soulcode.vscode-unwanted-extensions"
    )  # cspell:ignore Soulcode
    changes += vscode.add_extension_recommendation(
        session, "stkb.rewrap"
    )  # cspell:ignore stkb
    changes += vscode.remove_extension_recommendation(
        session,
        "garaioag.garaio-vscode-unwanted-recommendations",  # cspell:ignore garaio garaioag
        unwanted=True,
    )
    changes += vscode.remove_extension_recommendation(
        session,
        "travisillig.vscode-json-stable-stringify",  # cspell:ignore travisillig
        unwanted=True,
    )
    changes += vscode.remove_extension_recommendation(
        session,
        "tyriar.sort-lines",  # cspell:ignore tyriar
        unwanted=True,
    )
    return changes


def _update_settings(
    session: Session,
    /,
    has_notebooks: bool,
    is_python_repo: bool,
    package_manager: PackageManagerChoice,
) -> Changelog:
    changes = vscode.update_settings(
        session,
        {
            "diffEditor.experimental.showMoves": True,
            "editor.formatOnSave": True,
            "gitlens.telemetry.enabled": False,
            "multiDiffEditor.experimental.enabled": True,
            "redhat.telemetry.enabled": False,
            "telemetry.telemetryLevel": "off",
        },
    )
    changes += vscode.update_settings(
        session,
        {
            "[git-commit]": {
                "editor.rulers": [72],
                "rewrap.wrappingColumn": 72,
            },
            "[json]": {
                "editor.wordWrap": "on",
            },
        },
    )
    changes += _remove_outdated_settings(session)
    changes += _update_doc_settings(session)
    if has_notebooks:
        changes += _update_notebook_settings(session)
    changes += _update_pytest_settings(session)
    if has_constraint_files():
        changes += vscode.update_settings(
            session,
            {"files.associations": {"**/.constraints/py*.txt": "pip-requirements"}},
        )
    if is_python_repo:
        if package_manager == "pixi":
            python_path = ".pixi/envs/default/bin/python"
        else:
            python_path = ".venv/bin/python"
        changes += vscode.update_settings(
            session,
            {
                "python.defaultInterpreterPath": python_path,
                "rewrap.wrappingColumn": 88,
            },
        )
        if CONFIG_PATH.envrc.exists():
            changes += vscode.update_settings(
                session, {"python.terminal.activateEnvironment": False}
            )
    return changes


def _remove_outdated_settings(session: Session, /) -> Changelog:
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
    return vscode.remove_settings(session, outdated_settings)


def _update_doc_settings(session: Session, /) -> Changelog:
    if not os.path.exists("docs/"):
        return []
    changes = vscode.update_settings(
        session, {"livePreview.defaultPreviewPath": "docs/_build/html"}
    )
    changes += vscode.add_extension_recommendation(session, "ms-vscode.live-server")
    # cspell:ignore executablebookproject
    myst_extension = "executablebookproject.myst-highlight"
    if myst_extension not in vscode.get_unwanted_extensions(session):
        changes += vscode.add_extension_recommendation(session, myst_extension)
    return changes


def _update_notebook_settings(session: Session, /) -> Changelog:
    """https://code.visualstudio.com/updates/v1_83#_go-to-symbol-in-notebooks."""
    if not os.path.exists("docs/"):
        return []
    return vscode.update_settings(
        session, {"notebook.gotoSymbols.showAllSymbols": True}
    )


def _update_pytest_settings(session: Session, /) -> Changelog:
    if not os.path.exists("tests/"):
        return []
    return vscode.update_settings(
        session,
        {
            "python.testing.pytestEnabled": True,
            "python.testing.unittestEnabled": False,
        },
    )
