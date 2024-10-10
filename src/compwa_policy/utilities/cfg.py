"""Helper functions for formatting :file:`.cfg` files."""

from __future__ import annotations

import io
import re
from configparser import ConfigParser
from pathlib import Path
from typing import Callable, Iterable

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import read, write


def format_config(
    input: Path | io.TextIOBase | str,  # noqa: A002
    output: Path | io.TextIOBase | str,
    additional_rules: Iterable[Callable[[str], str]] | None = None,
) -> None:
    content = read(input)
    indent_size = 4
    # replace tabs
    content = content.replace("\t", indent_size * " ")
    # format spaces before comments (two spaces like black does)
    content = re.sub(r"([^\s^\n])[^\S\r\n]+#\s*([^\s])", r"\1  # \2", content)
    # remove trailing white-space
    content = re.sub(r"([^\S\r\n]+)\n", r"\n", content)
    # only two white-lines
    while "\n\n\n" in content:
        content = content.replace("\n\n\n", "\n\n")
    # end file with one and only one newline
    content = content.strip()
    content += "\n"
    if additional_rules is not None:
        for rule in additional_rules:
            content = rule(content)
    write(content, target=output)


def open_config(definition: Path | io.TextIOBase | str) -> ConfigParser:
    cfg = ConfigParser()
    if isinstance(definition, io.TextIOBase):
        text = definition.read()
        cfg.read_string(text)
    elif isinstance(definition, (Path, str)):
        if isinstance(definition, str):
            path = Path(definition)
        else:
            path = definition
        if not path.exists():
            msg = f'Config file "{path}" does not exist'
            raise PrecommitError(msg)
        cfg.read(path)
    else:
        msg = (
            f"Cannot create a {ConfigParser.__name__} from a"
            f" {type(definition).__name__}"
        )
        raise TypeError(msg)
    return cfg


def write_config(cfg: ConfigParser, output: Path | io.TextIOBase | str) -> None:
    if isinstance(output, io.TextIOBase):
        cfg.write(output)
    elif isinstance(output, (Path, str)):
        with open(output) as stream:
            cfg.write(stream)
    else:
        msg = f"Cannot write a {ConfigParser.__name__} to a {type(output).__name__}"
        raise TypeError(msg)
