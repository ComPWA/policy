"""Check the configuration for cspell.

See `cSpell
<https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell>`_.
"""

import json
import os

from repoma.pre_commit_hooks.errors import PrecommitError

__EXPECTED_CONFIG_FILE = ".cspell.json"


def check_cspell_config(fix: bool) -> None:
    _check_has_config()
    _fix_config_name(fix)
    _sort_config_entries(fix)


def _check_has_config() -> None:
    if not os.path.exists(__EXPECTED_CONFIG_FILE) and not os.path.exists(
        "cspell.json"
    ):
        raise PrecommitError(
            "This repository contains no .cspell.json config file"
        )


def _fix_config_name(fix: bool) -> None:
    if os.path.exists("cspell.json"):
        if fix:
            os.rename("cspell.json", __EXPECTED_CONFIG_FILE)
        raise PrecommitError(
            f'Config file for cSpell should be named "{__EXPECTED_CONFIG_FILE}"'
        )


def _sort_config_entries(fix: bool) -> None:
    with open(__EXPECTED_CONFIG_FILE) as stream:
        config = json.load(stream)
    error_message = ""
    for section, section_content in config.items():
        if not isinstance(section_content, list):
            continue
        sorted_section_content = sorted(section_content)
        if sorted_section_content == section_content:
            continue
        indent = 4 * " "
        error_message += (
            f'Section "{section}" in cSpell config '
            f'"./{__EXPECTED_CONFIG_FILE}" is not alphabetically sorted.'
        )
        if fix:
            config[section] = sorted_section_content
            error_message += " Problem has been fixed."
        else:
            json_content = map(lambda s: f'"{s}"', sorted_section_content)
            error_message += " Content should be:\n\n"
            error_message += f'{indent}"{section}": [\n{2 * indent}'
            error_message += f",\n{2 * indent}".join(json_content)
            error_message += f"\n{indent}]\n"
        break
    if fix:
        with open(__EXPECTED_CONFIG_FILE, "w") as stream:
            json.dump(config, stream, indent=4, ensure_ascii=False)
    if error_message:
        raise PrecommitError(error_message)
