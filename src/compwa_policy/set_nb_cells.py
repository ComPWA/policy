"""Add or update standard cells in a Jupyter notebook.

Notebook servers like Google Colaboratory and Deepnote do not install a package
automatically, so this has to be done through a code cell. At the same time,
this cell needs to be hidden from the documentation pages, when viewing through
Jupyter Lab (Binder), and when viewing as Jupyter slides.

This scripts sets the IPython InlineBackend.figure_formats option to SVG. This
is because the Sphinx configuration can't set this externally.

Notebooks can be ignored by making the first cell a `Markdown cell
<https://jupyter-notebook.readthedocs.io/en/latest/examples/Notebook/Working%20With%20Markdown%20Cells.html>`_
and writing the following `Markdown comment
<https://www.markdownguide.org/hacks/#comments>`_:

.. code-block:: markdown

    <!-- no-set-nb-cells -->
"""

from __future__ import annotations

import argparse
import sys
from functools import lru_cache
from textwrap import dedent
from typing import TYPE_CHECKING

import nbformat

from compwa_policy.utilities.notebook import load_notebook
from compwa_policy.utilities.pyproject import Pyproject

if TYPE_CHECKING:
    from collections.abc import Sequence

__CONFIG_CELL_CONTENT = """
import os

STATIC_WEB_PAGE = {"EXECUTE_NB", "READTHEDOCS"}.intersection(os.environ)
"""
__CONFIG_CELL_METADATA: dict = {
    "hideCode": True,
    "hideOutput": True,
    "hidePrompt": True,
    "jupyter": {"source_hidden": True},
    "tags": ["remove-cell"],
}

__INSTALL_CELL_METADATA: dict = {
    **__CONFIG_CELL_METADATA,
    "tags": ["remove-cell", "skip-execution"],
    # https://github.com/executablebooks/jupyter-book/issues/833
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    parser.add_argument(
        "--add-install-cell",
        action="store_true",
        help="Add notebook cell with pip install statement.",
    )
    parser.add_argument(
        "--extras-require",
        default="",
        help="Comma-separated list of optional dependencies, e.g. doc,viz",
        type=str,
    )
    parser.add_argument(
        "--additional-packages",
        default="",
        help="Comma-separated list of packages that should be installed with pip",
        type=str,
    )
    parser.add_argument(
        "--no-autolink-concat",
        default="",
        help=(
            "Do not add a cell with a autolink-concat directive. See"
            " https://sphinx-codeautolink.rtfd.io/en/latest/reference.html#directive-autolink-concat"
        ),
        type=str,
    )
    parser.add_argument(
        "--no-config-cell",
        action="store_true",
        help="Do not add configuration cell.",
    )
    args = parser.parse_args(argv)

    for filename in args.filenames:
        cell_id = 0
        if args.add_install_cell:
            cell_content = __get_install_cell().strip("\n")
            if args.extras_require:
                extras = args.extras_require.strip()
                cell_content += f"[{extras}]"
            if args.additional_packages:
                packages = [s.strip() for s in args.additional_packages.split(",")]
                cell_content += " " + " ".join(packages)
            _update_cell(
                filename,
                new_content=cell_content,
                new_metadata=__INSTALL_CELL_METADATA,
                cell_id=cell_id,
            )
            cell_id += 1
        if not args.no_config_cell:
            config_cell_content = __CONFIG_CELL_CONTENT
            _update_cell(
                filename,
                new_content=config_cell_content.strip("\n"),
                new_metadata=__CONFIG_CELL_METADATA,
                cell_id=cell_id,
            )
        _insert_autolink_concat(filename)
    return 0


@lru_cache(maxsize=1)
def __get_install_cell() -> str:
    package_name = Pyproject.load().get_package_name(raise_on_missing=True)
    msg = f"""
    # WARNING: advised to install a specific version, e.g. {package_name}==0.1.2
    %pip install -q {package_name}
    """
    return dedent(msg)


def _update_cell(
    filename: str,
    new_content: str,
    new_metadata: dict,
    cell_id: int,
) -> None:
    if _skip_notebook(filename):
        return
    notebook = load_notebook(filename)
    exiting_cell = notebook["cells"][cell_id]
    new_cell = nbformat.v4.new_code_cell(
        new_content,
        metadata=new_metadata,
    )
    del new_cell["id"]  # following nbformat_minor = 4
    if exiting_cell["cell_type"] == "code":
        notebook["cells"][cell_id] = new_cell
    else:
        notebook["cells"].insert(cell_id, new_cell)
    nbformat.validate(notebook)
    nbformat.write(notebook, filename)


def _insert_autolink_concat(filename: str) -> None:
    if _skip_notebook(filename, ignore_statement="<!-- no autolink-concat -->"):
        return
    notebook = load_notebook(filename)
    expected_cell_content = """
    ```{autolink-concat}
    ```
    """
    expected_cell_content = dedent(expected_cell_content).strip()
    for cell_id, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "markdown":
            continue
        cell_content: str = cell["source"]
        if cell_content == expected_cell_content:
            return
        new_cell = nbformat.v4.new_markdown_cell(expected_cell_content)
        del new_cell["id"]  # following nbformat_minor = 4
        notebook["cells"].insert(cell_id, new_cell)
        nbformat.validate(notebook)
        nbformat.write(notebook, filename)
        return


def _skip_notebook(
    filename: str, ignore_statement: str = "<!-- no-set-nb-cells -->"
) -> bool:
    notebook = load_notebook(filename)
    for cell in notebook["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        cell_content: str = cell["source"]
        if ignore_statement in cell_content.lower():
            return True
    return False


if __name__ == "__main__":
    sys.exit(main())
