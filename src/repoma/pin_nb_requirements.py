"""Enforce adding a pip install statement in the notebook.

In the `compwa-org repo <https://github.com/ComPWA/compwa-org>`_, notebooks
should specify which package versions should be used to run the notebook. This
hook checks whether a notebook has such install statements and whether they
comply with the expected formatting.
"""

import argparse
import sys
from functools import lru_cache
from typing import List, Optional, Sequence

import nbformat
from nbformat import NotebookNode

from repoma.utilities.executor import Executor
from repoma.utilities.notebook import load_notebook

from .errors import PrecommitError

__PIP_INSTALL_STATEMENT = "%pip install -q"


def check_pinned_requirements(filename: str) -> None:
    notebook = load_notebook(filename)
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
        executor(__check_install_statement, filename, cell_content)
        executor(__check_requirements, filename, cell_content)
        executor(__sort_requirements, filename, cell_content, notebook, cell_id)
        executor(__update_metadata, filename, cell["metadata"], notebook)
        executor.finalize()
        return
    msg = (
        f'Notebook "{filename}" does not contain a pip install cell of the form'
        f" {__PIP_INSTALL_STATEMENT} some-package==0.1.0 package2==3.2"
    )
    raise PrecommitError(msg)


def __has_python_kernel(notebook: dict) -> bool:
    # cspell:ignore kernelspec
    metadata = notebook.get("metadata", {})
    kernel_specification = metadata.get("kernelspec", {})
    kernel_language = kernel_specification.get("language", "")
    return "python" in kernel_language


def __check_install_statement(filename: str, install_statement: str) -> None:
    if not install_statement.startswith(__PIP_INSTALL_STATEMENT):
        msg = (
            f"First shell cell in notebook {filename} does not start with"
            f" {__PIP_INSTALL_STATEMENT}"
        )
        raise PrecommitError(msg)
    if install_statement.endswith("/dev/null"):
        msg = (
            "Remove the /dev/null from the pip install statement in notebook"
            f" {filename}"
        )
        raise PrecommitError(msg)


def __check_requirements(filename: str, install_statement: str) -> None:
    requirements = __extract_requirements(install_statement)
    if len(requirements) == 0:
        msg = f'At least one dependency required in install cell of "{filename}"'
        raise PrecommitError(msg)
    for requirement in requirements:
        requirement = requirement.strip()
        if not requirement:
            continue
        if "git+" in requirement:
            continue
        if not any(equal_sign in requirement for equal_sign in ["==", "~="]):
            msg = (
                f'Install cell in notebook "{filename}" contains a requirement without'
                f" == or ~= ({requirement})"
            )
            raise PrecommitError(msg)


def __sort_requirements(
    filename: str, install_statement: str, notebook: NotebookNode, cell_id: int
) -> None:
    requirements = __extract_requirements(install_statement)
    git_requirements = {r for r in requirements if r.startswith("git+")}
    pip_requirements = set(requirements) - git_requirements
    pip_requirements = {r.lower().replace("_", "-") for r in pip_requirements}
    sorted_requirements = sorted(pip_requirements) + sorted(git_requirements)
    if sorted_requirements != requirements:
        new_source = f"{__PIP_INSTALL_STATEMENT} {' '.join(sorted_requirements)}"
        notebook["cells"][cell_id]["source"] = new_source
        nbformat.write(notebook, filename)
        msg = f'Ordered and formatted pip install cell  in "{filename}"'
        raise PrecommitError(msg)


@lru_cache(maxsize=1)
def __extract_requirements(install_statement: str) -> List[str]:
    package_listing = install_statement.replace(__PIP_INSTALL_STATEMENT, "")
    requirements = package_listing.split(" ")
    requirements = [r.strip() for r in requirements]
    return [r for r in requirements if r]


def __update_metadata(filename: str, metadata: dict, notebook: NotebookNode) -> None:
    updated_metadata = False
    jupyter_metadata = metadata.get("jupyter")
    if jupyter_metadata is not None and jupyter_metadata.get("source_hidden"):
        if len(jupyter_metadata) == 1:
            metadata.pop("jupyter")
        else:
            jupyter_metadata.pop("source_hidden")
        updated_metadata = True
    tags = set(metadata.get("tags", []))
    expected_tags = {"remove-cell"}
    if expected_tags != tags:
        metadata["tags"] = sorted(expected_tags)
        updated_metadata = True
    if updated_metadata:
        nbformat.write(notebook, filename)
        msg = f'Updated metadata of pip install cell in notebook "{filename}"'
        raise PrecommitError(msg)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    args = parser.parse_args(argv)

    errors: List[PrecommitError] = []
    for filename in args.filenames:
        try:
            check_pinned_requirements(filename)
        except PrecommitError as exception:
            errors.append(exception)
    if errors:
        for error in errors:
            error_msg = "\n ".join(error.args)
            print(error_msg)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
