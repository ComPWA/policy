"""A collection of scripts that check the file structure of a repository."""

import argparse
import sys
from typing import Optional, Sequence

from repoma.pre_commit_hooks.errors import PrecommitError

from .check_labels import check_has_labels
from .cspell_config import check_cspell_config
from .editor_config_hook import check_editor_config_hook


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Dummy for pre-commit")
    parser.add_argument(
        "--no-fix",
        default=False,
        action="store_true",
        help="Fix the identified problems.",
    )
    args = parser.parse_args(argv)
    fix = not args.no_fix
    try:
        check_editor_config_hook()
        check_has_labels(fix)
        check_cspell_config(fix)
        return 0
    except PrecommitError as exception:
        print(str("\n".join(exception.args)))
        return 1


if __name__ == "__main__":
    sys.exit(main())
