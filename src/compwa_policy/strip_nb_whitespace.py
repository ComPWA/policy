"""Remove whitespaces at the end of lines in notebook cells."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

import nbformat

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.notebook import load_notebook

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("notebooks", nargs="*", help="Notebooks to format")
    args = parser.parse_args(argv)

    with Executor(raise_exception=False) as do:
        for filename in args.notebooks:
            do(_strip_trailing_whitespace, filename)
    return 1 if do.error_messages else 0


def _strip_trailing_whitespace(filename: str) -> None:
    notebook = load_notebook(filename)
    updated = False
    for cell in notebook.get("cells", []):
        source = cell.get("source", "")
        if not isinstance(source, str):
            continue
        if source and source[-1].isspace():
            updated = True
            cell["source"] = source.rstrip()
    if updated:
        nbformat.write(notebook, filename)
        msg = f"Stripped trailing whitespace in {filename}"
        raise PrecommitError(msg)


if __name__ == "__main__":
    sys.exit(main())
