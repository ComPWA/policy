"""Check the configuration for cspell.

See `cSpell
<https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell>`_.
"""

import json
import os
from typing import Any, Sequence

from repoma.pre_commit_hooks.errors import PrecommitError

from ._helpers import REPOMA_DIR, add_badge, find_precommit_hook, remove_badge

__EXPECTED_CONFIG_PATH = ".cspell.json"
__PRETTIER_IGNORE_PATH = ".prettierignore"

# cspell:ignore pelling
# pylint: disable=line-too-long
__CSPELL_BADGE = "[![Spelling checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell)"
__CSPELL_BADGE_PATTERN = (
    r"\[\!\[[Ss]pelling.*\]\(.*cspell.*\)\]\(.*cspell.*\)\n?"
)

__JSON_DUMP_OPTIONS = {
    "indent": 4,
    "ensure_ascii": False,
}

with open(f"{REPOMA_DIR}/{__EXPECTED_CONFIG_PATH}") as __STREAM:
    __EXPECTED_CONFIG = json.load(__STREAM)


def fix_cspell_config(extend: bool) -> None:
    _rename_cspell_config()
    cspell_hook = find_precommit_hook(r".*/mirrors-cspell")
    if cspell_hook is None:
        _remove_cspell_configuration()
    else:
        _fix_config_content(extend)
        _sort_config_entries()
        _update_prettier_ignore()
        add_badge(f"{__CSPELL_BADGE}\n")


def _rename_cspell_config() -> None:
    if os.path.exists("cspell.json"):
        os.rename("cspell.json", __EXPECTED_CONFIG_PATH)


def _remove_cspell_configuration() -> None:
    if os.path.exists(__EXPECTED_CONFIG_PATH):
        os.remove(__EXPECTED_CONFIG_PATH)
        raise PrecommitError(
            f'"{__EXPECTED_CONFIG_PATH}" is no longer required'
            " and has been removed"
        )
    if os.path.exists(__PRETTIER_IGNORE_PATH):
        with open(__PRETTIER_IGNORE_PATH, "r") as stream:
            prettier_ignore_content = stream.readlines()
        expected_line = __EXPECTED_CONFIG_PATH + "\n"
        if expected_line in set(prettier_ignore_content):
            prettier_ignore_content.remove(expected_line)
            with open(__PRETTIER_IGNORE_PATH, "w") as stream:
                stream.writelines(prettier_ignore_content)
            raise PrecommitError(
                f'"{__EXPECTED_CONFIG_PATH}" in "./{__PRETTIER_IGNORE_PATH}"'
                " is no longer required and has been removed"
            )
    remove_badge(__CSPELL_BADGE_PATTERN)


def _fix_config_content(extend: bool) -> None:
    if not os.path.exists(__EXPECTED_CONFIG_PATH):
        with open(__EXPECTED_CONFIG_PATH, "w") as stream:
            stream.write("{}")
    with open(__EXPECTED_CONFIG_PATH) as stream:
        config = json.load(stream)
    fixed_sections = []
    for section in __EXPECTED_CONFIG:
        expected_section_content = __get_expected_content(
            config, section, extend=extend
        )
        section_content = config.get(section)
        if section_content == expected_section_content:
            continue
        fixed_sections.append('"' + section + '"')
        config[section] = expected_section_content
    if fixed_sections:
        with open(__EXPECTED_CONFIG_PATH, "w") as stream:
            json.dump(config, stream, **__JSON_DUMP_OPTIONS)  # type: ignore
        error_message = __express_list_of_sections(fixed_sections)
        error_message += f' in "./{__EXPECTED_CONFIG_PATH}" has been updated.'
        raise PrecommitError(error_message)


def _sort_config_entries() -> None:
    with open(__EXPECTED_CONFIG_PATH) as stream:
        config = json.load(stream)
    error_message = ""
    fixed_sections = []
    for section, section_content in config.items():
        if not isinstance(section_content, list):
            continue
        sorted_section_content = sorted(section_content)
        if section_content == sorted_section_content:
            continue
        fixed_sections.append('"' + section + '"')
        config[section] = sorted_section_content
    with open(__EXPECTED_CONFIG_PATH, "w") as stream:
        json.dump(config, stream, **__JSON_DUMP_OPTIONS)  # type: ignore
    if fixed_sections:
        error_message = __express_list_of_sections(fixed_sections)
        error_message += (
            ' in "./{__EXPECTED_CONFIG_FILE}" has been sorted alphabetically.'
        )
        raise PrecommitError(error_message)


def _update_prettier_ignore() -> None:
    prettier_hook = find_precommit_hook(r".*/mirrors-prettier")
    if prettier_hook is None:
        return
    prettier_ignore_path = ".prettierignore"
    expected_line = __EXPECTED_CONFIG_PATH + "\n"
    if not os.path.exists(prettier_ignore_path):
        with open(prettier_ignore_path, "w") as stream:
            stream.write(expected_line)
    else:
        with open(prettier_ignore_path, "r") as stream:
            prettier_ignore_content = stream.readlines()
        if expected_line in set(prettier_ignore_content):
            return
        with open(prettier_ignore_path, "w+") as stream:
            stream.write(expected_line)
    raise PrecommitError(
        f'Added "{__EXPECTED_CONFIG_PATH}" to "./{prettier_ignore_path}"'
    )


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


def __express_list_of_sections(sections: Sequence[str]) -> str:
    """Convert list of sections into natural language.

    >>> __express_list_of_sections(["one"])
    'Section one'
    >>> __express_list_of_sections(["one", "two"])
    'Sections one and two'
    >>> __express_list_of_sections(["one", "two", "three"])
    'Sections one, two, and three'
    >>> __express_list_of_sections([])
    ''
    """
    if not sections:
        return ""
    sentence = "Section"
    if len(sections) == 1:
        sentence += " " + sections[0]
    else:
        sentence += "s "
        sentence += ", ".join(sections[:-1])
        if len(sections) > 2:
            sentence += ","
        sentence += " and " + sections[-1]
    return sentence
