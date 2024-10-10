"""Check Tox configuration file."""

from __future__ import annotations

import re
from configparser import ConfigParser
from pathlib import Path
from typing import TYPE_CHECKING

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject
from compwa_policy.utilities.toml import to_multiline_string

if TYPE_CHECKING:
    from tomlkit.items import String


def main(has_notebooks: bool) -> None:
    _merge_tox_ini_into_pyproject()
    tox = read_tox_config()
    if tox is None:
        return
    _check_expected_sections(tox, has_notebooks)


def _merge_tox_ini_into_pyproject() -> None:
    if not CONFIG_PATH.tox.is_file():
        return
    with open(CONFIG_PATH.tox) as file:
        tox_ini = file.read()
    with ModifiablePyproject.load() as pyproject:
        tox_table = pyproject.get_table("tool.tox", create=True)
        tox_table["legacy_tox_ini"] = __ini_to_toml(tox_ini)
        CONFIG_PATH.tox.unlink()
        msg = f"Merged {CONFIG_PATH.tox} into {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def __ini_to_toml(ini: str) -> String:
    ini = re.sub(r"(?<!\\)(\\)(?!\n)", r"\\\\", ini)
    if not re.match(r"^  [^ ]", ini):
        ini = ini.replace("  ", "    ")
    ini = f"\n{ini.strip()}\n"
    return to_multiline_string(ini)


def _check_expected_sections(tox: ConfigParser, has_notebooks: bool) -> None:
    # cspell:ignore doclive docnb docnblive testenv
    sections: set[str] = set(tox)
    expected_sections: set[str] = set()
    if Path("docs").exists():
        expected_sections |= {
            "testenv:doc",
            "testenv:doclive",
        }
        if has_notebooks:
            expected_sections |= {
                "testenv:docnb",
                "testenv:docnblive",
                "testenv:nb",
            }
    missing_sections = expected_sections - sections
    if missing_sections:
        msg = (
            f"Tox configuration is missing job definitions:"
            f" {', '.join(sorted(missing_sections))}"
        )
        raise PrecommitError(msg)


def read_tox_config() -> ConfigParser | None:
    if CONFIG_PATH.tox.is_file():
        return _load_tox_ini()
    if CONFIG_PATH.pyproject.is_file():
        pyproject = Pyproject.load()
        if not pyproject.has_table("tool.tox"):
            return None
        tox_table = pyproject.get_table("tool.tox")
        tox_config_str = tox_table.get("legacy_tox_ini")
        if tox_config_str is not None:
            config = ConfigParser()
            config.read_string(tox_config_str)
    return None


def _load_tox_ini() -> ConfigParser:
    config = ConfigParser()
    config.read(CONFIG_PATH.tox)
    return config
