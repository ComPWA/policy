"""Check Tox configuration file."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject


def main(has_notebooks: bool) -> None:
    tox = read_tox_config()
    if tox is None:
        return
    _check_expected_sections(tox, has_notebooks)


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
        config = ConfigParser()
        config.read(CONFIG_PATH.tox)
        return config
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
