"""Check configuration of VS Code."""

from repoma.utilities.executor import Executor
from repoma.utilities.vscode import (
    remove_unwanted_recommendations,
    remove_vscode_extension_recommendation,
)


def main() -> None:
    executor = Executor()
    executor(_update_extensions)
    executor.finalize()


def _update_extensions() -> None:
    executor = Executor()
    executor(remove_unwanted_recommendations)
    executor(
        remove_vscode_extension_recommendation,
        "travisillig.vscode-json-stable-stringify",
        # cspell:ignore travisillig
    )
    executor.finalize()
