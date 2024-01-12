"""Format :code:`setup.cfg` if available."""

from __future__ import annotations

import argparse
import re
import sys
from typing import TYPE_CHECKING, Sequence

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.cfg import format_config
from compwa_policy.utilities.project_info import open_setup_cfg

if TYPE_CHECKING:
    import io
    from configparser import ConfigParser
    from pathlib import Path


def format_setup_cfg() -> None:
    cfg = open_setup_cfg()
    write_formatted_setup_cfg(cfg)


def write_formatted_setup_cfg(cfg: ConfigParser) -> None:
    with open(CONFIG_PATH.setup_cfg, "w") as stream:
        cfg.write(stream)
    _format_setup_cfg(
        input=CONFIG_PATH.setup_cfg,
        output=CONFIG_PATH.setup_cfg,
    )


def _format_setup_cfg(
    input: Path | (io.TextIOBase | str),  # noqa: A002
    output: Path | (io.TextIOBase | str),
) -> None:
    def format_version_constraints(content: str) -> str:
        content = re.sub(r"(>=?|<=?|==)\s+", r"\1", content)
        content = re.sub(r"([^\s])(>=?|<=?)", r"\1 \2", content)
        return re.sub(r"([^\s])\s\s+(>=?|<=?)", r"\1 \2", content)

    format_config(
        input=input,
        output=output,
        additional_rules=[
            format_version_constraints,
        ],
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("filenames", nargs="*", help="Filenames to check.")
    args = parser.parse_args(argv)
    if str(CONFIG_PATH.setup_cfg) in args.filenames:
        format_setup_cfg()
    return 0


if __name__ == "__main__":
    sys.exit(main())
