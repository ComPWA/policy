"""Check contents of a ``tox.ini`` file."""

import os
from configparser import ConfigParser
from copy import deepcopy
from typing import List, Tuple

from repoma.pre_commit_hooks.errors import PrecommitError

__CONFIG_PATH = "tox.ini"


def check_tox_ini(fix: bool) -> None:
    if not os.path.exists(__CONFIG_PATH):
        return
    extract_sections(["flake8"], output_file=".flake8", fix=fix)
    extract_sections(["pydocstyle"], output_file=".pydocstyle", fix=fix)
    extract_sections(
        ["coverage:run", "pytest"], output_file="pytest.ini", fix=fix
    )


def extract_sections(sections: List[str], output_file: str, fix: bool) -> None:
    cfg = ConfigParser()
    cfg.read(__CONFIG_PATH)
    if any(map(cfg.has_section, sections)):
        error_message = (
            f'Section "{", ".join(sections)}"" in "./{__CONFIG_PATH}" '
        )
        if fix:
            old_cfg, extracted_cfg = __split_config(cfg, sections)
            __write_config(old_cfg, __CONFIG_PATH)
            __write_config(extracted_cfg, output_file)
            error_message += (
                f'has been extracted to a "./{output_file}" config file.'
            )
        else:
            error_message += (
                f'should be defined in a separate "{output_file}" config file.'
            )
        raise PrecommitError(error_message)


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


def __write_config(cfg: ConfigParser, output_path: str) -> None:
    with open(output_path, "w") as stream:
        cfg.write(stream)
    __format_config_file(output_path)


def __format_config_file(path: str) -> None:
    with open(path, "r") as stream:
        content = stream.read()
    indent_size = 4
    content = content.replace("\t", indent_size * " ")
    content = content.replace("\\\n", "\\\n" + indent_size * " ")
    while "  #" in content:
        content = content.replace("  #", " #")
    while " \n" in content:
        content = content.replace(" \n", "\n")
    content = content.strip()
    content += "\n"
    with open(path, "w") as stream:
        stream.write(content)
