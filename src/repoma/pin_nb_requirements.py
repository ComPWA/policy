"""Enforce adding a pip install statement in the notebook.

In the `compwa-org repo <https://github.com/ComPWA/compwa-org>_`, notebooks
should specify which package versions should be used to run the notebook. This
hook checks whether a notebook has such install statements and whether they
comply with the expected formatting.
"""
# cspell:ignore notebooknode
import argparse
from typing import List, Optional, Sequence

import nbformat
from nbformat.notebooknode import NotebookNode

from repoma.errors import PrecommitError
from repoma.utilities._notebook import get_pip_target_dir
from repoma.utilities.executor import Executor

__PIP_INSTALL_STATEMENT = "%pip install"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    args = parser.parse_args(argv)

    executor = Executor()
    for filename in args.filenames:
        executor(check_pinned_requirements, filename)
    return executor.finalize(exception=False)


def check_pinned_requirements(filename: str) -> None:
    notebook: NotebookNode = nbformat.read(filename, as_version=nbformat.NO_CONVERT)
    if not __has_python_kernel(notebook):
        return
    for cell_id, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source: str = cell["source"]
        src_lines = source.split("\n")
        if len(src_lines) == 0:
            continue
        cell_content = "".join(s.strip("\\") for s in src_lines)
        if not cell_content.startswith(__PIP_INSTALL_STATEMENT):
            continue
        executor = Executor()
        executor(__check_requirement_pinning, filename, cell_id, cell_content)
        executor(__update_install_statement, filename, notebook, cell_id, cell_content)
        executor(__update_metadata, filename, notebook, cell_id)
        executor.finalize()


def __has_python_kernel(notebook: dict) -> bool:
    # cspell:ignore kernelspec
    metadata = notebook.get("metadata", {})
    kernel_specification = metadata.get("kernelspec", {})
    kernel_language = kernel_specification.get("language", "")
    return "python" in kernel_language


def __check_requirement_pinning(filename: str, cell_id: int, cell_content: str) -> None:
    requirements = __get_notebook_requirements(cell_content)
    for package in requirements:
        if not package:
            continue
        if "git+" in package:
            continue
        if not any(equal_sign in package for equal_sign in ["==", "~="]):
            msg = (
                f'Install cell ({cell_id}) in notebook "{filename}" contains a'
                f" requirement without == or ~= ({package})"
            )
            raise PrecommitError(msg)


def __update_install_statement(
    filename: str, notebook: NotebookNode, cell_id: int, cell_content: str
) -> None:
    requirements = __get_notebook_requirements(cell_content)
    pip_requirements = sorted(r for r in requirements if not r.startswith("git+"))
    git_requirements = sorted(r for r in requirements if r.startswith("git+"))
    sorted_requirements = pip_requirements + git_requirements
    pip_target_dir = get_pip_target_dir(filename)
    requirements_str = " ".join(sorted_requirements)
    expected = (
        f"{__PIP_INSTALL_STATEMENT} {requirements_str} -qq --target={pip_target_dir}"
    )
    if cell_content != expected:
        metadata = notebook["cells"][cell_id]["metadata"]
        if "jupyter" in metadata:
            metadata["jupyter"]["source_hidden"] = True
        else:
            metadata["jupyter"] = {"source_hidden": True}
        new_cell = nbformat.v4.new_code_cell(
            expected,
            metadata=metadata,
        )
        del new_cell["id"]  # following nbformat_minor = 4
        notebook["cells"][cell_id] = new_cell
        nbformat.validate(notebook)
        nbformat.write(notebook, filename)
        msg = f"Updated pip install cell in {filename}"
        raise PrecommitError(msg)


def __get_notebook_requirements(install_statement: str) -> List[str]:
    package_listing = install_statement.replace(__PIP_INSTALL_STATEMENT, "")
    packages = package_listing.split(" ")
    packages = [p.strip() for p in packages]
    return [p for p in packages if p and p if not p.startswith("-")]


def __update_metadata(filename: str, notebook: NotebookNode, cell_id: int) -> None:
    updated = False
    metadata = notebook["cells"][cell_id]["metadata"]
    source_hidden = metadata.get("jupyter", {}).get("source_hidden")
    if not source_hidden:
        if "jupyter" in metadata:
            metadata["jupyter"]["source_hidden"] = True
        else:
            metadata["jupyter"] = {"source_hidden": True}
        updated = True
    tags = set(metadata.get("tags", []))
    expected_tags = {"remove-cell"}
    if expected_tags != tags:
        metadata["tags"] = sorted(tags)
        updated = True
    if updated:
        nbformat.validate(notebook)
        nbformat.write(notebook, filename)
        msg = f"Updated metadata of cell {cell_id} in notebook {filename}"
        raise PrecommitError(msg)


if __name__ == "__main__":
    raise SystemExit(main())
