"""Enforce adding a pip install statement in the notebook.

In the `compwa-org repo <https://github.com/ComPWA/compwa-org>_`, notebooks
should specify which package versions should be used to run the notebook. This
hook checks whether a notebook has such install statements and whether they
comply with the expected formatting.
"""

import argparse
import sys
import textwrap
from typing import List, Optional, Sequence

import nbformat  # type: ignore

from .errors import PrecommitError

__INDENT_SIZE = 2
__INDENT = __INDENT_SIZE * " "


def check_pinned_requirements(filename: str) -> None:
    notebook = nbformat.read(filename, as_version=nbformat.NO_CONVERT)
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        source: str = cell["source"]
        src_lines = source.split("\n")
        if src_lines[0] != "%%sh":
            continue
        second_line = src_lines[1]
        if not second_line.startswith("pip install "):
            raise PrecommitError(
                f'First shell cell in notebook  "{filename}"'
                " does not run pip install"
            )
        if not second_line.endswith(" > /dev/null"):
            raise PrecommitError(
                f'Install statement in notebook "{filename}" should end with'
                ' " > /dev/null" in order to suppress stdout'
            )
        if len(src_lines) != 2:
            source = textwrap.indent(source, prefix=__INDENT)
            raise PrecommitError(
                f'Install cell in notebook "{filename}" has more than 2 lines:'
                f"\n\n{source}"
            )
        requirements = second_line.split(" ")
        if len(requirements) <= 4:
            raise PrecommitError(
                "At least one dependency required in install cell of "
                f'"{filename}"'
            )
        requirements = requirements[2:-2]
        for requirement in requirements:
            if "==" not in requirement:
                raise PrecommitError(
                    f'Install cell in notebook "{filename}" contains a'
                    f" requirement without == ({requirement})"
                )
        return
    raise PrecommitError(
        f'Notebook "{filename}" does not contain a pip install cell'
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
