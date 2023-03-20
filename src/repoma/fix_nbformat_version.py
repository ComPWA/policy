"""Set nbformat minor version to 4.

nbformat adds random cell ids since version 5.x. This is annoying for git
diffs. The solution is to set the version to v4 and removes those cell ids.
"""

import argparse
import sys
from textwrap import dedent
from typing import Optional, Sequence

import nbformat

from .errors import PrecommitError
from .utilities.executor import Executor

BINARY_CELL_OUTPUT = [
    "image/jpeg",
    "image/png",
    "image/svg+xml",
]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to fix.")
    args = parser.parse_args(argv)
    executor = Executor()
    for filename in args.filenames:
        executor(set_nbformat_version, filename)
        executor(remove_cell_ids, filename)
        executor(check_svg_output_cells, filename)
    return executor.finalize(exception=False)


def set_nbformat_version(filename: str) -> None:
    notebook = open_notebook(filename)
    if notebook["nbformat_minor"] != 4:
        notebook["nbformat_minor"] = 4
        nbformat.write(notebook, filename)


def remove_cell_ids(filename: str) -> None:
    notebook = open_notebook(filename)
    for cell in notebook["cells"]:
        if "id" in cell:
            del cell["id"]
    nbformat.write(notebook, filename)


def check_svg_output_cells(filename: str) -> None:
    notebook = open_notebook(filename)
    for i, cell in enumerate(notebook["cells"]):
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            for binary in BINARY_CELL_OUTPUT:
                if binary in data:
                    # pylint: disable=line-too-long
                    error_message = f"""
                    Cell {i} in {filename} contains {binary} output. Please
                    store it somewhere outside this repository and render it
                    through an external link. See for instance
                    https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files
                    """
                    raise PrecommitError(
                        dedent(error_message).strip().replace("\n", " ")
                    )


def open_notebook(filename: str) -> dict:
    return nbformat.read(filename, as_version=nbformat.NO_CONVERT)


if __name__ == "__main__":
    sys.exit(main())
