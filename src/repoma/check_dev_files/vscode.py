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
    _update_pytest_settings()
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
