"""Check the configuration for cspell.

See `cSpell
<https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell>`_.
"""

import json
import os
from typing import Any

import repoma
from repoma.pre_commit_hooks.errors import PrecommitError

__EXPECTED_CONFIG_FILE = ".cspell.json"
__REPOMA_DIR = os.path.dirname(repoma.__file__)
with open(f"{__REPOMA_DIR}/{__EXPECTED_CONFIG_FILE}") as __STREAM:
    __EXPECTED_CONFIG = json.load(__STREAM)

__JSON_DUMP_OPTIONS = {
    "indent": 4,
    "ensure_ascii": False,
}


def check_cspell_config(fix: bool, extend: bool) -> None:
    _check_has_config()
    _fix_config_name(fix)
    _fix_config_content(fix, extend)
    _sort_config_entries(fix)


def _check_has_config() -> None:
    if not os.path.exists(__EXPECTED_CONFIG_FILE) and not os.path.exists(
        "cspell.json"
    ):
        raise PrecommitError(
            f"This repository contains no {__EXPECTED_CONFIG_FILE} config file"
        )


def _fix_config_name(fix: bool) -> None:
    if os.path.exists("cspell.json"):
        if fix:
            os.rename("cspell.json", __EXPECTED_CONFIG_FILE)
        raise PrecommitError(
            f'Config file for cSpell should be named "{__EXPECTED_CONFIG_FILE}"'
        )


def _fix_config_content(fix: bool, extend: bool) -> None:
    with open(__EXPECTED_CONFIG_FILE) as stream:
        config = json.load(stream)
    error_message = ""
    for section in __EXPECTED_CONFIG:
        expected_section_content = __get_expected_content(
            config, section, extend=extend
        )
        section_content = config.get(section)
        if section_content == expected_section_content:
            continue
        error_message += (
            f'Section "{section}" in cSpell config '
            f'"./{__EXPECTED_CONFIG_FILE}" is missing expected entries.'
        )
        config[section] = expected_section_content
        if fix:
            error_message += " Problem has been fixed."
        else:
            error_message += " Content should be:\n\n"
            error_message += __render_section(config, section)
            error_message += "\n"
        break
    if fix:
        with open(__EXPECTED_CONFIG_FILE, "w") as stream:
            json.dump(config, stream, **__JSON_DUMP_OPTIONS)  # type: ignore
    if error_message:
        raise PrecommitError(error_message)


def __get_expected_content(config: dict, section: str, *, extend: bool) -> Any:
    if section not in config:
        return __EXPECTED_CONFIG[section]
    section_content = config[section]
    if section not in __EXPECTED_CONFIG:
        return section_content
    expected_section_content = __EXPECTED_CONFIG[section]
    if isinstance(expected_section_content, str):
        return expected_section_content
    if isinstance(expected_section_content, list):
        if not extend:
            return sorted(expected_section_content)
        expected_section_content_set = set(expected_section_content)
        expected_section_content_set.update(section_content)
        return sorted(expected_section_content_set)
    raise NotImplementedError(
        "No implementation for section content of type"
        f' {section_content.__class__.__name__} (section: "{section}"'
    )


def _sort_config_entries(fix: bool) -> None:
    with open(__EXPECTED_CONFIG_FILE) as stream:
        config = json.load(stream)
    error_message = ""
    for section, section_content in config.items():
        if not isinstance(section_content, list):
            continue
        sorted_section_content = sorted(section_content)
        if section_content == sorted_section_content:
            continue
        error_message += (
            f'Section "{section}" in cSpell config '
            f'"./{__EXPECTED_CONFIG_FILE}" is not alphabetically sorted.'
        )
        config[section] = sorted_section_content
        if fix:
            error_message += " Problem has been fixed."
        else:
            error_message += " Content should be:\n\n"
            error_message += __render_section(config, section)
            error_message += "\n"
        break
    if fix:
        with open(__EXPECTED_CONFIG_FILE, "w") as stream:
            json.dump(config, stream, **__JSON_DUMP_OPTIONS)  # type: ignore
    if error_message:
        raise PrecommitError(error_message)


def __render_section(config: dict, section: str) -> str:
    output = json.dumps(
        {section: config[section]},
        **__JSON_DUMP_OPTIONS,  # type: ignore
    )
    output = "\n".join(output.split("\n")[1:-1])
    return output
