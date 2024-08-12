"""Check configuration of VS Code."""

import os

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.python import has_constraint_files


def main(has_notebooks: bool) -> None:
    with Executor() as do:
        do(_update_extensions)
        do(_update_settings, has_notebooks)


def _update_extensions() -> None:
    with Executor() as do:
        do(
            vscode.add_extension_recommendation,
            "stkb.rewrap",  # cspell:ignore stkb
        )
        do(
            vscode.remove_extension_recommendation,
            "travisillig.vscode-json-stable-stringify",  # cspell:ignore travisillig
            unwanted=True,
        )
        do(
            vscode.remove_extension_recommendation,
            "tyriar.sort-lines",  # cspell:ignore tyriar
            unwanted=True,
        )
        do(
            vscode.remove_extension_recommendation,
            "garaioag.garaio-vscode-unwanted-recommendations",  # cspell:ignore garaio garaioag
            unwanted=True,
        )
        do(
            vscode.add_extension_recommendation,
            "Soulcode.vscode-unwanted-extensions",  # cspell:ignore Soulcode
        )
        do(
            vscode.add_extension_recommendation,
            "mhutchie.git-graph",  # cspell:ignore mhutchie
        )


def _update_settings(has_notebooks: bool) -> None:
    with Executor() as do:
        do(
            vscode.update_settings,
            {
                "diffEditor.experimental.showMoves": True,
                "editor.formatOnSave": True,
                "gitlens.telemetry.enabled": False,
                "multiDiffEditor.experimental.enabled": True,
                "redhat.telemetry.enabled": False,
                "rewrap.wrappingColumn": 88,  # black
                "telemetry.telemetryLevel": "off",
            },
        )
        do(
            vscode.update_settings,
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
        do(_remove_outdated_settings)
        do(_update_doc_settings)
        if has_notebooks:
            do(_update_notebook_settings)
        do(_update_pytest_settings)
        if has_constraint_files():
            do(
                vscode.update_settings,
                {"files.associations": {"**/.constraints/py*.txt": "pip-requirements"}},
            )
        if CONFIG_PATH.envrc.exists():
            do(vscode.update_settings, {"python.terminal.activateEnvironment": False})


def _remove_outdated_settings() -> None:
    outdated_settings = [
        "editor.rulers",
        "githubPullRequests.telemetry.enabled",
        "gitlens.advanced.telemetry.enabled",
        "python.analysis.diagnosticMode",
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
    vscode.remove_settings(outdated_settings)


def _update_doc_settings() -> None:
    if not os.path.exists("docs/"):
        return
    settings = {
        "livePreview.defaultPreviewPath": "docs/_build/html",
    }
    with Executor() as do:
        do(vscode.update_settings, settings)
        do(
            vscode.add_extension_recommendation,
            "executablebookproject.myst-highlight",  # cspell:ignore executablebookproject
        )
        do(vscode.add_extension_recommendation, "ms-vscode.live-server")


def _update_notebook_settings() -> None:
    """https://code.visualstudio.com/updates/v1_83#_go-to-symbol-in-notebooks."""
    if not os.path.exists("docs/"):
        return
    settings = {
        "notebook.gotoSymbols.showAllSymbols": True,
    }
    vscode.update_settings(settings)


def _update_pytest_settings() -> None:
    if not os.path.exists("tests/"):
        return
    pytest_settings = {
        "python.analysis.inlayHints.pytestParameters": True,
        "python.testing.pytestEnabled": True,
        "python.testing.unittestEnabled": False,
    }
    vscode.update_settings(pytest_settings)
