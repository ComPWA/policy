"""Add install statements to first cell in a Jupyter notebook.

Google Colaboratory does not install a package automatically, so this has to be
done through a code cell. At the same time, this cell needs to be hidden from
the documentation pages, when viewing through Jupyter Lab (Binder), and when
viewing Jupyter slides.

Additionally, this scripts sets the IPython InlineBackend.figure_formats option
to SVG. This is because the Sphinx configuration can't set this externally.

Notebooks can be ignored by making the first cell a `Markdown cell
<https://jupyter-notebook.readthedocs.io/en/latest/examples/Notebook/Working%20With%20Markdown%20Cells.html>`_
and starting its content with:

.. code-block:: markdown

    <!-- ignore first cell -->
"""

import argparse
import sys
from typing import Optional, Sequence

import nbformat

from repoma.utilities.setup_cfg import open_setup_cfg

__SETUP_CFG = open_setup_cfg()
__PACKAGE_NAME = __SETUP_CFG["metadata"]["name"]
__DEFAULT_CONTENT = """
%%capture
%config Completer.use_jedi = False
%config InlineBackend.figure_formats = ['svg']
import os

STATIC_WEB_PAGE = {"EXECUTE_NB", "READTHEDOCS"}.intersection(os.environ)
"""
__COLAB_CONTENT = f"""
# Install on Google Colab
import subprocess
import sys

from IPython import get_ipython

install_packages = "google.colab" in str(get_ipython())
if install_packages:
    for package in ["{__PACKAGE_NAME}[doc]", "graphviz"]:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package]
        )
"""

__EXPECTED_CELL_METADATA = {
    "hideCode": True,
    "hideOutput": True,
    "hidePrompt": True,
    "jupyter": {"source_hidden": True},
    "slideshow": {"slide_type": "skip"},
    "tags": ["remove-cell"],
}


def fix_first_cell(
    filename: str, new_content: str, replace: bool = False
) -> None:
    notebook = nbformat.read(filename, as_version=nbformat.NO_CONVERT)
    old_cell = notebook["cells"][0]
    if old_cell["cell_type"] == "markdown":
        old_cell_content: str = old_cell["source"]
        old_cell_content = old_cell_content.lower()
        first_line = old_cell_content.split("\n")[0]
        first_line = first_line.strip()
        if (
            first_line.startswith("<!--")
            and first_line.endswith("-->")
            and "ignore" in first_line
            and "cell" in first_line
        ):
            return
    new_cell = nbformat.v4.new_code_cell(
        new_content,
        metadata=__EXPECTED_CELL_METADATA,
    )
    del new_cell["id"]  # following nbformat_minor = 4
    if replace:
        notebook["cells"][0] = new_cell
    else:
        notebook["cells"] = [new_cell] + notebook["cells"]
    nbformat.validate(notebook)
    nbformat.write(notebook, filename)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace first cell instead of prepending a new cell.",
    )
    parser.add_argument(
        "--colab",
        action="store_true",
        help="Add pip install statements for Google Colab.",
    )
    args = parser.parse_args(argv)

    expected_cell_content = __DEFAULT_CONTENT.strip("\n")
    if args.colab:
        expected_cell_content += "\n\n"
        expected_cell_content += __COLAB_CONTENT.strip("\n")
    exit_code = 0
    for filename in args.filenames:
        fix_first_cell(
            filename,
            new_content=expected_cell_content,
            replace=args.replace,
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())