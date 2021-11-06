"""Enforce adding a pip install statement in the notebook.

In the `compwa-org repo <https://github.com/ComPWA/compwa-org>_`, notebooks
should specify which package versions should be used to run the notebook. This
hook checks whether a notebook has such install statements and whether they
comply with the expected formatting.
"""

import argparse
import sys
from typing import TYPE_CHECKING

import nbformat

from .errors import PrecommitError

if TYPE_CHECKING:
    from typing import List, Optional, Sequence


def check_pinned_requirements(filename: str) -> None:
    notebook = nbformat.read(filename, as_version=nbformat.NO_CONVERT)
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        source: str = cell["source"]
        src_lines = source.split("\n")
        if len(src_lines) == 0:
            continue
        if src_lines[0] != "%%sh":
            continue
        if len(src_lines) != 2:
            raise PrecommitError(
                f'Install cell in notebook "{filename}" has more than 2 lines'
            )
        install_statement = src_lines[1]
        __check_install_statement(filename, install_statement)
        __check_requirements(filename, install_statement)
        __check_metadata(filename, cell["metadata"])
        return
    raise PrecommitError(
        f'Notebook "{filename}" does not contain a pip install cell'
    )


def __check_install_statement(filename: str, install_statement: str) -> None:
    if not install_statement.startswith("pip install "):
        raise PrecommitError(
            f'First shell cell in notebook  "{filename}"'
            " does not run pip install"
        )
    if not install_statement.endswith(" > /dev/null"):
        raise PrecommitError(
            f'Install statement in notebook "{filename}" should end with'
            ' " > /dev/null" in order to suppress stdout'
        )


def __check_requirements(filename: str, install_statement: str) -> None:
    requirements = install_statement.split(" ")
    if len(requirements) <= 4:
        raise PrecommitError(
            f'At least one dependency required in install cell of "{filename}"'
        )
    requirements = requirements[2:-2]
    for requirement in requirements:
        requirement = requirement.strip()
        if not requirement:
            continue
        if "==" not in requirement:
            raise PrecommitError(
                f'Install cell in notebook "{filename}" contains a'
                f" requirement without == ({requirement})"
            )
    requirements_lower = [r.lower() for r in requirements]
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
    tags = metadata.get("tags")
    expected_tag = "hide-cell"
    if tags is None or expected_tag not in tags:
        raise PrecommitError(
            f'Install cell in notebook "{filename}" should have tag'
            f' "{expected_tag}"'
        )
    if "remove-cell" in tags:
        raise PrecommitError(
            f'Install cell in notebook "{filename}" has tag "remove-cell"'
        )


def main(argv: "Optional[Sequence[str]]" = None) -> int:
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
