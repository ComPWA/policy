"""Format :code:`setup.cfg` if available."""

import argparse
import io
import re
import sys
from typing import TYPE_CHECKING

from repoma._utilities import CONFIG_PATH, format_config, open_setup_cfg

if TYPE_CHECKING:
    from configparser import ConfigParser
    from pathlib import Path
    from typing import Optional, Sequence, Union


def format_setup_cfg() -> None:
    cfg = open_setup_cfg()
    write_formatted_setup_cfg(cfg)


def write_formatted_setup_cfg(cfg: "ConfigParser") -> None:
    with open(CONFIG_PATH.setup_cfg, "w") as stream:
        cfg.write(stream)
    _format_setup_cfg(
        input=CONFIG_PATH.setup_cfg,
        output=CONFIG_PATH.setup_cfg,
    )


def _format_setup_cfg(
    input: "Union[Path, io.TextIOBase, str]",  # noqa: A002
    output: "Union[Path, io.TextIOBase, str]",
) -> None:
    def format_version_constraints(content: str) -> str:
        content = re.sub(r"(>=?|<=?|==)\s+", r"\1", content)
        content = re.sub(r"([^\s])(>=?|<=?)", r"\1 \2", content)
        content = re.sub(r"([^\s])\s\s+(>=?|<=?)", r"\1 \2", content)
        return content

    format_config(
        input=input,
        output=output,
        additional_rules=[
            format_version_constraints,
        ],
    )


def main(argv: "Optional[Sequence[str]]" = None) -> int:
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
    if str(CONFIG_PATH.setup_cfg) in args.filenames:
        format_setup_cfg()
    return 0


if __name__ == "__main__":
    sys.exit(main())
