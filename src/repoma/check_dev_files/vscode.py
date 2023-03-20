"""Check configuration of VS Code."""

from repoma.utilities.vscode import remove_unwanted_recommendations


def main() -> None:
    _update_extensions()


def _update_extensions() -> None:
    remove_unwanted_recommendations()
