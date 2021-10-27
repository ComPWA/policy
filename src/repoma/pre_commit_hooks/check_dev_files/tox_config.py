"""Check contents of a ``tox.ini`` file."""

from configparser import ConfigParser
from pathlib import Path
from typing import List, Tuple, Union

from repoma._utilities import CONFIG_PATH, copy_config
from repoma.pre_commit_hooks.errors import PrecommitError


def check_tox_ini() -> None:
    if not CONFIG_PATH.tox.exists():
        return
    extract_sections(["flake8"], output_file=".flake8")
    extract_sections(["pydocstyle"], output_file=".pydocstyle")
    extract_sections(["coverage:run", "pytest"], output_file="pytest.ini")


def extract_sections(sections: List[str], output_file: str) -> None:
    cfg = ConfigParser()
    cfg.read(CONFIG_PATH.tox)
    if any(map(cfg.has_section, sections)):
        old_cfg, extracted_cfg = __split_config(cfg, sections)
        __write_config(old_cfg, CONFIG_PATH.tox)
        __write_config(extracted_cfg, output_file)
        raise PrecommitError(
            f'Section "{", ".join(sections)}"" in "./{CONFIG_PATH.tox}"'
            f' has been extracted to a "./{output_file}" config file.'
        )


def __split_config(
    cfg: ConfigParser, extracted_sections: List[str]
) -> Tuple[ConfigParser, ConfigParser]:
    old_config = copy_config(cfg)
    extracted_config = copy_config(cfg)
    for section in cfg.sections():
        if section in extracted_sections:
            old_config.remove_section(section)
        else:
            extracted_config.remove_section(section)
    return old_config, extracted_config


def __write_config(cfg: ConfigParser, output_path: Union[Path, str]) -> None:
    with open(output_path, "w") as stream:
        cfg.write(stream)
    __format_config_file(output_path)


def __format_config_file(path: Union[Path, str]) -> None:
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
