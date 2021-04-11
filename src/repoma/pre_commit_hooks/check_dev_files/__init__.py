"""A collection of scripts that check the file structure of a repository."""

import argparse
import sys
from typing import Optional, Sequence

from .check_labels import check_has_labels_toml


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--no-fix",
        default=False,
        action="store_true",
        help="Fix the identified problems.",
    )
    args = parser.parse_args(argv)
    check_has_labels_toml(fix=not args.no_fix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
