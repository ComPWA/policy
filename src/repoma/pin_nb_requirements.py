"""Enforce adding a pip install statement in the notebook.

In the `compwa-org repo <https://github.com/ComPWA/compwa-org>_`, notebooks
should specify which package versions should be used to run the notebook. This
hook checks whether a notebook has such install statements and whether they
comply with the expected formatting.
"""

import argparse
import sys
from typing import List, Optional, Sequence

import nbformat

from .errors import PrecommitError

__PIP_INSTALL_STATEMENT = "%pip install -q "


def check_pinned_requirements(filename: str) -> None:
    notebook = nbformat.read(filename, as_version=nbformat.NO_CONVERT)
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        source: str = cell["source"]
        src_lines = source.split("\n")
        if len(src_lines) == 0:
            continue
        cell_content = "".join(s.strip("\\") for s in src_lines)
        if not cell_content.startswith(__PIP_INSTALL_STATEMENT):
            continue
        __check_install_statement(filename, cell_content)
        __check_requirements(filename, cell_content)
        __check_metadata(filename, cell["metadata"])
        return
    raise PrecommitError(
        f'Notebook "{filename}" does not contain a pip install cell of the'
        f" form {__PIP_INSTALL_STATEMENT}some-package==0.1.0 package2==3.2"
    )


def __check_install_statement(filename: str, install_statement: str) -> None:
    if not install_statement.startswith(__PIP_INSTALL_STATEMENT):
        raise PrecommitError(
            f"First shell cell in notebook {filename} does not start with"
            f" {__PIP_INSTALL_STATEMENT}"
        )
    if install_statement.endswith("/dev/null"):
        raise PrecommitError(
            "Remove the /dev/null from the pip install statement in notebook"
            f" {filename}"
        )


def __check_requirements(  # noqa: R701
    filename: str, install_statement: str
) -> None:
    package_listing = install_statement.replace(__PIP_INSTALL_STATEMENT, "")
    requirements = package_listing.split(" ")
    if len(requirements) == 0:
        raise PrecommitError(
            f'At least one dependency required in install cell of "{filename}"'
        )
    for requirement in requirements:
        requirement = requirement.strip()
        if not requirement:
            continue
        if "git+" in requirement:
            continue
        if "==" not in requirement:
            raise PrecommitError(
                f'Install cell in notebook "{filename}" contains a'
                f" requirement without == ({requirement})"
            )
    requirements_lower = [
        r.lower() for r in requirements if not r.startswith("git+")
    ]
    if sorted(requirements_lower) != requirements_lower:
        sorted_requirements = " ".join(sorted(requirements))
        raise PrecommitError(
            f'Requirements in notebook "{filename}"'
            " are not sorted alphabetically. Should be:\n\n  "
            f"  {sorted_requirements}"
        )


def __check_metadata(filename: str, metadata: dict) -> None:
    source_hidden = metadata.get("jupyter", {}).get("source_hidden")
    if not source_hidden:
        raise PrecommitError(
            f'Install cell in notebook "{filename}" is not hidden'
        )
    tags = set(metadata.get("tags", []))
    expected_tags = {"remove-cell"}
    if expected_tags != tags:
        raise PrecommitError(
            f'Install cell in notebook "{filename}" should have tags'
            f" {sorted(expected_tags)}"
        )


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
            print(error_msg)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
