"""Remove tags metadata from notebook cells if they are empty."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

import nbformat

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import filter_files
from compwa_policy.utilities.notebook import load_notebook
from compwa_policy.utilities.pyproject import Pyproject, has_dependency

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    args = parser.parse_args(argv)

    with Executor(raise_exception=False) as do:
        for filename in args.filenames:
            do(_set_nb_display_name, filename)
    return 1 if do.error_messages else 0


def _set_nb_display_name(filename: str) -> None:
    notebook = load_notebook(filename)
    display_name = (
        notebook.get("metadata", {})
        .get("kernelspec", {})  # cspell:ignore kernelspec
        .get("display_name")
    )
    expected_display_name = "Python 3 (ipykernel)"
    if filter_files(["pyproject.toml"]):
        pyproject = Pyproject.load()
        if has_dependency(pyproject, "pyproject-local-kernel"):
            expected_display_name = "Pyproject Local"
    if display_name != expected_display_name:
        if "metadata" not in notebook:
            notebook["metadata"] = {}
        metadata = notebook["metadata"]
        if "kernelspec" not in metadata:
            metadata["kernelspec"] = {}
        metadata["kernelspec"]["display_name"] = expected_display_name
        nbformat.write(notebook, filename)
        msg = f"Set display name to {expected_display_name!r} in {filename}"
        raise PrecommitError(msg)


if __name__ == "__main__":
    sys.exit(main())
