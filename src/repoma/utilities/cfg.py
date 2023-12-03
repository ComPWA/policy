"""Helper functions for formatting :file:`.cfg` files."""

import io
import re
from configparser import ConfigParser
from copy import deepcopy
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple, Union

from repoma.errors import PrecommitError

from . import CONFIG_PATH, read, write


def extract_config_section(
    extract_from: Union[Path, str],
    extract_to: Union[Path, str],
    sections: List[str],
) -> None:
    cfg = open_config(extract_from)
    if any(map(cfg.has_section, sections)):
        old_cfg, extracted_cfg = __split_config(cfg, sections)
        __write_config(old_cfg, extract_from)
        __write_config(extracted_cfg, extract_to)
        msg = (
            f'Section "{", ".join(sections)}"" in "./{CONFIG_PATH.tox}" has been'
            f' extracted to a "./{extract_to}" config file.'
        )
        raise PrecommitError(msg)


def __split_config(
    cfg: ConfigParser, extracted_sections: List[str]
) -> Tuple[ConfigParser, ConfigParser]:
    old_config = deepcopy(cfg)
    extracted_config = deepcopy(cfg)
    for section in cfg.sections():
        if section in extracted_sections:
            old_config.remove_section(section)
        else:
            extracted_config.remove_section(section)
    return old_config, extracted_config


def __write_config(cfg: ConfigParser, output_path: Union[Path, str]) -> None:
    with open(output_path, "w") as stream:
        cfg.write(stream)
    format_config(input=output_path, output=output_path)


def format_config(
    input: Union[Path, io.TextIOBase, str],  # noqa: A002
    output: Union[Path, io.TextIOBase, str],
    additional_rules: Optional[Iterable[Callable[[str], str]]] = None,
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


def open_config(definition: Union[Path, io.TextIOBase, str]) -> ConfigParser:
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


def write_config(cfg: ConfigParser, output: Union[Path, io.TextIOBase, str]) -> None:
    if isinstance(output, io.TextIOBase):
        cfg.write(output)
    elif isinstance(output, (Path, str)):
        with open(output) as stream:
            cfg.write(stream)
    else:
        msg = f"Cannot write a {ConfigParser.__name__} to a {type(output).__name__}"
        raise TypeError(msg)
