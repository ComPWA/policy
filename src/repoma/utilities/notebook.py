"""Helper tools for working with Jupyter Notebooks."""

import nbformat
from nbformat import NotebookNode


def load_notebook(path: str) -> NotebookNode:
    return nbformat.read(path, as_version=nbformat.NO_CONVERT)
