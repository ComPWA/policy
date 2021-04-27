"""Format :code:`setup.cfg` if available."""

import argparse
import sys
from configparser import ConfigParser
from typing import Optional, Sequence


def format_setup_cfg() -> None:
    cfg = ConfigParser()
    cfg.read("setup.cfg")
    with open("setup.cfg", "w") as stream:
        cfg.write(stream)
    with open("setup.cfg") as stream:
        content = stream.read()
    content = "\n".join(  # remove trailing spaces
        map(lambda line: line.rstrip(), content.split("\n"))
    )
    content = content.replace("\t", 4 * " ")  # replace tabs
    content = content.replace("  #", " #")  # remove spaces before comments
    content = content.replace(" #", "  #")  # black: two spaces before comment
    content = content.strip("\n") + "\n"  # remove final line ending
    with open("setup.cfg", "w") as stream:
        stream.write(content)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace first cell instead of prepending a new cell.",
    )
    parser.add_argument(
        "--colab",
        action="store_true",
        help="Add pip install statements for Google Colab.",
    )
    args = parser.parse_args(argv)
    if "setup.cfg" in args.filenames:
        format_setup_cfg()
    return 0


if __name__ == "__main__":
    sys.exit(main())
