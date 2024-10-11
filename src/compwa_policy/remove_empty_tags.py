"""Remove tags metadata from notebook cells if they are empty."""

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
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    args = parser.parse_args(argv)

    with Executor(raise_exception=False) as do:
        for filename in args.filenames:
            do(_remove_cells, filename)
    return 1 if do.error_messages else 0


def _remove_cells(filename: str) -> None:
    notebook = load_notebook(filename)
    updated = False
    for cell in notebook["cells"]:
        metadata = cell["metadata"]
        tags = metadata.get("tags")
        if tags is None:
            continue
        if not tags:
            metadata.pop("tags")
            updated = True
    if updated:
        nbformat.write(notebook, filename)
        msg = f'Removed empty tags cell metadata from "{filename}"'
        raise PrecommitError(msg)


if __name__ == "__main__":
    sys.exit(main())
