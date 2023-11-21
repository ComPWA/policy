"""Add notebook metadata to open the TOC sidebar on Google Colab.

See `ComPWA/repo-maintenance#40 <https://github.com/ComPWA/repo-maintenance/issues/40>`_
for more information.
"""

import argparse
import sys
from typing import Optional, Sequence

import nbformat

from repoma.utilities.notebook import load_notebook

from .errors import PrecommitError
from .utilities.executor import Executor


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "filenames",
        nargs="*",
        help="Paths to the notebooks of which the metadata should be updated.",
    )
    args = parser.parse_args(argv)
    executor = Executor()
    for filename in args.filenames:
        executor(_update_metadata, filename)
    return executor.finalize(exception=False)


def _update_metadata(path: str) -> None:
    notebook = load_notebook(path)
    metadata = notebook["metadata"]
    updated = False
    if metadata.get("colab") is None:
        updated = True
        metadata["colab"] = {}
    if not metadata["colab"].get("toc_visible"):
        updated = True
        metadata["colab"]["toc_visible"] = True
    if not updated:
        return
    nbformat.write(notebook, path)
    msg = f"Colab TOC is now visible for notebook {path}"
    raise PrecommitError(msg)


if __name__ == "__main__":
    sys.exit(main())
