"""Check configuration of VS Code."""

import os

from repoma.utilities import vscode
from repoma.utilities.executor import Executor


def main() -> None:
    executor = Executor()
    executor(_update_extensions)
    executor(_update_settings)
    executor.finalize()


def _update_extensions() -> None:
    executor = Executor()
    executor(vscode.remove_unwanted_recommendations)
    executor(
        vscode.remove_extension_recommendation,
        "travisillig.vscode-json-stable-stringify",
        # cspell:ignore travisillig
    )
    executor.finalize()


def _update_settings() -> None:
    executor = Executor()
    executor(_remove_outdated_settings)
    executor(_update_doc_settings)
    executor(_update_pytest_settings)
    executor.finalize()


def _remove_outdated_settings() -> None:
    outdated_settings = [
        "telemetry.telemetryLevel",
    ]
    vscode.remove_settings(outdated_settings)


def _update_doc_settings() -> None:
    if not os.path.exists("docs/"):
        return
    settings = {
        "livePreview.defaultPreviewPath": "docs/_build/html",
    }
    executor = Executor()
    executor(vscode.set_setting, settings)
    executor(vscode.add_extension_recommendation, "ms-vscode.live-server")
    executor.finalize()


def _update_pytest_settings() -> None:
    if not os.path.exists("tests/"):
        return
    pytest_settings = {
        "python.analysis.inlayHints.pytestParameters": True,
        "python.testing.pytestEnabled": True,
        "python.testing.unittestEnabled": False,
    }
    vscode.set_setting(pytest_settings)
