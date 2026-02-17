"""Add or update standard cells in a Jupyter notebook.

Notebook servers like Google Colaboratory and Deepnote do not install a package
automatically, so this has to be done through a code cell. At the same time, this cell
needs to be hidden from the documentation pages, when viewing through Jupyter Lab
(Binder), and when viewing as Jupyter slides.

This scripts sets the IPython InlineBackend.figure_formats option to SVG. This is
because the Sphinx configuration can't set this externally.

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
from typing import TYPE_CHECKING, cast

import nbformat
from nbformat import NotebookNode

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
__AUTOLINK_CONCAT = """
:::{autolink-concat}
:::
""".strip()


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
        "--autolink-concat",
        action="store_true",
        help="Add a cell with a autolink-concat directive. See https://sphinx-codeautolink.rtfd.io/en/latest/reference.html#directive-autolink-concat",
    )
    parser.add_argument(
        "--config-cell",
        action="store_true",
        help="Add configuration cell.",
    )
    args = parser.parse_args(argv)

    failed = False
    for filename in args.filenames:
        cell_id = 0
        updated = False
        notebook = load_notebook(filename)
        if args.add_install_cell:
            cell_content = __get_install_cell().strip("\n")
            if args.extras_require:
                extras = args.extras_require.strip()
                cell_content += f"[{extras}]"
            if args.additional_packages:
                packages = [s.strip() for s in args.additional_packages.split(",")]
                cell_content += " " + " ".join(packages)
            updated |= _update_cell(
                notebook,
                new_content=cell_content,
                new_metadata=__INSTALL_CELL_METADATA,
                cell_id=cell_id,
            )
            cell_id += 1
        if args.config_cell:
            config_cell_content = __CONFIG_CELL_CONTENT
            updated |= _update_cell(
                filename,
                new_content=config_cell_content.strip("\n"),
                new_metadata=__CONFIG_CELL_METADATA,
                cell_id=cell_id,
            )
        if args.autolink_concat and not _skip_notebook(
            notebook, ignore_comment="<!-- no autolink-concat -->"
        ):
            updated |= _format_autolink_concat(notebook)
            updated |= _insert_autolink_concat(notebook)
            if (n_autolink := _count_autolink_concat(notebook)) > 1:
                failed |= True
                print(  # noqa: T201
                    f"Found {n_autolink} autolink-concat cells in {filename}, should be"
                    " only one. Please remove duplicates.",
                    file=sys.stderr,
                )
        if updated:
            print(f"Updated {filename}", file=sys.stderr)  # noqa: T201
            nbformat.validate(notebook)
            nbformat.write(notebook, filename)
            failed |= True
    if failed:
        return 1
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
    notebook: NotebookNode,
    new_content: str,
    new_metadata: dict,
    cell_id: int,
) -> bool:
    if _skip_notebook(notebook, ignore_comment="<!-- no-set-nb-cells -->"):
        return False
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
    return True


def _format_autolink_concat(notebook: NotebookNode) -> bool:
    candidates = [
        ":::{autolink-concat}\n\n:::",
        "```{autolink-concat}\n\n```",
        "```{autolink-concat}\n```",
    ]
    updated = False
    for cell in notebook["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        for pattern in candidates:
            source = cast("str", cell["source"])
            if pattern in source:
                cell["source"] = source.replace(pattern, __AUTOLINK_CONCAT)
                updated |= True
    return updated


def _insert_autolink_concat(notebook: NotebookNode) -> bool:
    if any(
        __AUTOLINK_CONCAT in cell["source"]
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    ):
        return False
    for cell_id, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "markdown":
            continue
        new_cell = nbformat.v4.new_markdown_cell(__AUTOLINK_CONCAT)
        del new_cell["id"]  # following nbformat_minor = 4
        notebook["cells"].insert(cell_id, new_cell)
        return True
    return False


def _count_autolink_concat(notebook: NotebookNode) -> int:
    search_terms = [
        "```{autolink-concat}",
        ":::{autolink-concat}",
    ]
    count = 0
    for cell in notebook["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        cell_content: str = cell["source"]
        if any(term in cell_content for term in search_terms):
            count += 1
    return count


def _skip_notebook(notebook: NotebookNode, ignore_comment: str) -> bool:
    for cell in notebook["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        cell_content: str = cell["source"]
        if ignore_comment in cell_content.lower():
            return True
    return False


if __name__ == "__main__":
    sys.exit(main())
