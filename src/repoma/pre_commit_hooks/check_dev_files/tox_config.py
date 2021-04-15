"""Check contents of a ``tox.ini`` file."""

from configparser import ConfigParser
from copy import deepcopy
from typing import Tuple

from repoma.pre_commit_hooks.errors import PrecommitError

from ._helpers import check_has_file

__EXPECTED_CONFIG_FILE = "tox.ini"


def check_tox_ini(fix: bool) -> None:
    check_has_file(__EXPECTED_CONFIG_FILE)
    extract_section("flake8", output_file=".flake8", fix=fix)
    extract_section("pydocstyle", output_file=".pydocstyle", fix=fix)


def extract_section(section: str, output_file: str, fix: bool) -> None:
    cfg = ConfigParser()
    cfg.read(__EXPECTED_CONFIG_FILE)
    if cfg.has_section(section):
        error_message = f'Section "{section}" in "./{__EXPECTED_CONFIG_FILE}" '
        if fix:
            old_cfg, extracted_cfg = __split_config(cfg, section)
            __write_config(old_cfg, __EXPECTED_CONFIG_FILE)
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
    cfg: ConfigParser, extracted_section: str
) -> Tuple[ConfigParser, ConfigParser]:
    old_config = deepcopy(cfg)
    extracted_config = deepcopy(cfg)
    old_config.remove_section(extracted_section)
    for section in cfg.sections():
        if section != extracted_section:
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
