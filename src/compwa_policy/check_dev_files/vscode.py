"""Check configuration of VS Code."""

import os

from compwa_policy.utilities import vscode
from compwa_policy.utilities.executor import Executor


def main(has_notebooks: bool) -> None:
    executor = Executor()
    executor(_update_extensions)
    executor(_update_settings, has_notebooks)
    executor.finalize()


def _update_extensions() -> None:
    executor = Executor()
    executor(
        vscode.add_extension_recommendation,
        "stkb.rewrap",  # cspell:ignore stkb
    )
    executor(
        vscode.remove_extension_recommendation,
        "travisillig.vscode-json-stable-stringify",
        # cspell:ignore travisillig
        unwanted=True,
    )
    executor(
        vscode.remove_extension_recommendation,
        "tyriar.sort-lines",  # cspell:ignore tyriar
        unwanted=True,
    )
    executor(
        vscode.remove_extension_recommendation,
        "garaioag.garaio-vscode-unwanted-recommendations",
        # cspell:ignore garaio garaioag
        unwanted=True,
    )
    executor(
        vscode.add_extension_recommendation,
        "Soulcode.vscode-unwanted-extensions",
        # cspell:ignore Soulcode
    )
    executor.finalize()


def _update_settings(has_notebooks: bool) -> None:
    executor = Executor()
    executor(
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
    executor(
        vscode.update_settings,
        {
            "[git-commit]": {
                "editor.rulers": [72],
                "rewrap.wrappingColumn": 72,
            },
        },
    )
    executor(_remove_outdated_settings)
    executor(_update_doc_settings)
    if has_notebooks:
        executor(_update_notebook_settings)
    executor(_update_pytest_settings)
    executor.finalize()


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
    executor = Executor()
    executor(vscode.update_settings, settings)
    executor(
        vscode.add_extension_recommendation,
        "executablebookproject.myst-highlight",  # cspell:ignore executablebookproject
    )
    executor(vscode.add_extension_recommendation, "ms-vscode.live-server")
    executor.finalize()


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
