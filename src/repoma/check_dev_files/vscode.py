"""Check configuration of VS Code."""

from repoma.utilities import vscode
from repoma.utilities.executor import Executor


def main() -> None:
    executor = Executor()
    executor(_update_extensions)
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
