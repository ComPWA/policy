"""Check Tox configuration file."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH


def main(has_notebooks: bool) -> None:
    if not CONFIG_PATH.tox.exists():
        return
    tox = _read_tox_config(CONFIG_PATH.tox)
    _check_expected_sections(tox, has_notebooks)


def _read_tox_config(path: Path) -> ConfigParser:
    config = ConfigParser()
    config.read(path)
    return config


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
            f"{CONFIG_PATH.tox} is missing job definitions:"
            f" {', '.join(sorted(missing_sections))}"
        )
        raise PrecommitError(msg)
