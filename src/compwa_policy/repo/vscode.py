"""Check configuration of VS Code."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.python import has_constraint_files

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.config import PackageManagerChoice
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Session


@check_hook(
    group="repo",
    paths=[CONFIG_PATH.envrc],
    directories=(CONFIG_PATH.pip_constraints, ".vscode"),
)
def check(session: Session, args: Arguments, ctx: CheckContext) -> None:
    _update_extensions(session)
    _update_settings(
        session,
        ctx.has_notebooks,
        ctx.is_python_repo,
        args.package_manager,
    )


def _update_extensions(session: Session, /) -> None:
    # cspell:disable
    vscode.add_extension_recommendation(session, "eamodio.gitlens")
    vscode.add_extension_recommendation(session, "mhutchie.git-graph")
    vscode.add_extension_recommendation(session, "soulcode.vscode-unwanted-extensions")
    vscode.add_extension_recommendation(session, "stkb.rewrap")
    vscode.remove_extension_recommendation(
        session,
        "garaioag.garaio-vscode-unwanted-recommendations",
        unwanted=True,
    )
    vscode.remove_extension_recommendation(
        session,
        "travisillig.vscode-json-stable-stringify",
        unwanted=True,
    )
    vscode.remove_extension_recommendation(session, "tyriar.sort-lines", unwanted=True)
    # cspell:enable


def _update_settings(
    session: Session,
    /,
    has_notebooks: bool,
    is_python_repo: bool,
    package_manager: PackageManagerChoice,
) -> None:
    vscode.update_settings(
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
    vscode.update_settings(
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
    _remove_outdated_settings(session)
    _update_doc_settings(session)
    if has_notebooks:
        _update_notebook_settings(session)
    _update_pytest_settings(session)
    if has_constraint_files():
        vscode.update_settings(
            session,
            {"files.associations": {"**/.constraints/py*.txt": "pip-requirements"}},
        )
    if is_python_repo:
        if package_manager == "pixi":
            python_path = ".pixi/envs/default/bin/python"
        else:
            python_path = ".venv/bin/python"
        vscode.update_settings(
            session,
            {
                "python.defaultInterpreterPath": python_path,
                "rewrap.wrappingColumn": 88,
            },
        )
        if CONFIG_PATH.envrc.exists():
            vscode.update_settings(
                session, {"python.terminal.activateEnvironment": False}
            )


def _remove_outdated_settings(session: Session, /) -> None:
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
    vscode.remove_settings(session, outdated_settings)


def _update_doc_settings(session: Session, /) -> None:
    if not os.path.exists("docs/"):
        return
    vscode.update_settings(
        session, {"livePreview.defaultPreviewPath": "docs/_build/html"}
    )
    vscode.add_extension_recommendation(session, "ms-vscode.live-server")
    # cspell:ignore executablebookproject
    myst_extension = "executablebookproject.myst-highlight"
    if myst_extension not in vscode.get_unwanted_extensions(session):
        vscode.add_extension_recommendation(session, myst_extension)


def _update_notebook_settings(session: Session, /) -> None:
    """https://code.visualstudio.com/updates/v1_83#_go-to-symbol-in-notebooks."""
    if not os.path.exists("docs/"):
        return
    vscode.update_settings(session, {"notebook.gotoSymbols.showAllSymbols": True})


def _update_pytest_settings(session: Session, /) -> None:
    if not os.path.exists("tests/"):
        return
    vscode.update_settings(
        session,
        {
            "python.testing.pytestEnabled": True,
            "python.testing.unittestEnabled": False,
        },
    )
