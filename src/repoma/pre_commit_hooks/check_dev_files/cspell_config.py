"""Check the configuration for cspell.

See `cSpell
<https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell>`_.
"""

import itertools
import json
import os
import textwrap
from configparser import ConfigParser
from typing import Any, Sequence

import yaml

from repoma.pre_commit_hooks.errors import PrecommitError

from ._helpers import (
    REPOMA_DIR,
    add_badge,
    add_vscode_extension_recommendation,
    find_precommit_hook,
    remove_badge,
    remove_vscode_extension_recommendation,
    rename_config,
)

__CONFIG_PATH = ".cspell.json"
__EDITOR_CONFIG_PATH = ".editorconfig"
__PRETTIER_IGNORE_PATH = ".prettierignore"
__VSCODE_EXTENSION_NAME = "streetsidesoftware.code-spell-checker"

# cspell:ignore pelling
# pylint: disable=line-too-long
__BADGE = "[![Spelling checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell)"
__BADGE_PATTERN = r"\[\!\[[Ss]pelling.*\]\(.*cspell.*\)\]\(.*cspell.*\)\n?"
__HOOK_URL = "https://github.com/streetsidesoftware/cspell-cli"


with open(f"{REPOMA_DIR}/{__CONFIG_PATH}") as __STREAM:
    __EXPECTED_CONFIG = json.load(__STREAM)


def fix_cspell_config() -> None:
    rename_config("cspell.json", __CONFIG_PATH)
    _check_hook_url()
    precommit_hook = find_precommit_hook(__HOOK_URL)
    if precommit_hook is None:
        _remove_configuration()
    else:
        _check_check_hook_options()
        _fix_config_content()
        _sort_config_entries()
        _check_editor_config()
        _update_prettier_ignore()
        add_badge(f"{__BADGE}\n")
        add_vscode_extension_recommendation(__VSCODE_EXTENSION_NAME)


def _check_hook_url() -> None:
    old_url_patters = [
        r".*/mirrors-cspell",
    ]
    for pattern in old_url_patters:
        old_url = find_precommit_hook(pattern)
        if old_url is not None:
            raise PrecommitError(
                "Pre-commit hook for cspell should be updated."
                f" Repo URL should be {__HOOK_URL}"
            )


def _remove_configuration() -> None:
    if os.path.exists(__CONFIG_PATH):
        os.remove(__CONFIG_PATH)
        raise PrecommitError(
            f'"{__CONFIG_PATH}" is no longer required' " and has been removed"
        )
    if os.path.exists(__PRETTIER_IGNORE_PATH):
        with open(__PRETTIER_IGNORE_PATH, "r") as stream:
            prettier_ignore_content = stream.readlines()
        expected_line = __CONFIG_PATH + "\n"
        if expected_line in set(prettier_ignore_content):
            prettier_ignore_content.remove(expected_line)
            with open(__PRETTIER_IGNORE_PATH, "w") as stream:
                stream.writelines(prettier_ignore_content)
            raise PrecommitError(
                f'"{__CONFIG_PATH}" in "./{__PRETTIER_IGNORE_PATH}"'
                " is no longer required and has been removed"
            )
    remove_badge(__BADGE_PATTERN)
    remove_vscode_extension_recommendation(__VSCODE_EXTENSION_NAME)


def _check_check_hook_options() -> None:
    config = find_precommit_hook(__HOOK_URL)
    assert config is not None
    expected_yaml = f"""
  - repo: {__HOOK_URL}
    rev: ...
    hooks:
      - id: cspell
    """
    expected_config = yaml.safe_load(expected_yaml)[0]
    if (
        list(config) != list(expected_config)
        or config.get("hooks") != expected_config["hooks"]
    ):
        raise PrecommitError(
            "cSpell pre-commit hook should have the following form:\n"
            + expected_yaml
        )


def _fix_config_content() -> None:
    if not os.path.exists(__CONFIG_PATH):
        with open(__CONFIG_PATH, "w") as stream:
            stream.write("{}")
    config = __get_config(__CONFIG_PATH)
    fixed_sections = []
    for section_name in __EXPECTED_CONFIG:
        if section_name in {"words", "ignoreWords"}:
            if section_name not in config:
                fixed_sections.append('"' + section_name + '"')
                config[section_name] = []
            continue
        expected_section_content = __get_expected_content(config, section_name)
        section_content = config.get(section_name)
        if section_content == expected_section_content:
            continue
        fixed_sections.append('"' + section_name + '"')
        config[section_name] = expected_section_content
    if fixed_sections:
        __write_config(config)
        error_message = __express_list_of_sections(fixed_sections)
        error_message += f' in "./{__CONFIG_PATH}" has been updated.'
        raise PrecommitError(error_message)


def _sort_config_entries() -> None:
    config = __get_config(__CONFIG_PATH)
    error_message = ""
    fixed_sections = []
    for section, section_content in config.items():
        if not isinstance(section_content, list):
            continue
        sorted_section_content = sorted(
            section_content, key=lambda s: s.lower()
        )
        if section_content == sorted_section_content:
            continue
        fixed_sections.append('"' + section + '"')
        config[section] = sorted_section_content
    if fixed_sections:
        __write_config(config)
        error_message = __express_list_of_sections(fixed_sections)
        error_message += (
            f' in "./{__CONFIG_PATH}" has been sorted alphabetically.'
        )
        raise PrecommitError(error_message)


def _check_editor_config() -> None:
    if not os.path.exists(__EDITOR_CONFIG_PATH):
        return
    cfg = ConfigParser()
    with open(__EDITOR_CONFIG_PATH) as stream:
        # https://stackoverflow.com/a/24501036/13219025
        cfg.read_file(
            itertools.chain(["[global]"], stream),
            source=__EDITOR_CONFIG_PATH,
        )
    if not cfg.has_section(__CONFIG_PATH):
        raise PrecommitError(
            f'./{__EDITOR_CONFIG_PATH} has no section "[{__CONFIG_PATH}]"'
        )
    expected_options = {
        "indent_size": "4",
    }
    options = dict(cfg.items(__CONFIG_PATH))
    if options != expected_options:
        error_message = (
            f"./{__EDITOR_CONFIG_PATH} should have the following section:\n\n"
        )
        section_content = f"[{__CONFIG_PATH}]\n"
        for option, value in expected_options.items():
            section_content += f"{option} = {value}\n"
        section_content = textwrap.indent(section_content, prefix="  ")
        raise PrecommitError(error_message + section_content)


def _update_prettier_ignore() -> None:
    prettier_hook = find_precommit_hook(__HOOK_URL)
    if prettier_hook is None:
        return
    prettier_ignore_path = ".prettierignore"
    expected_line = __CONFIG_PATH + "\n"
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
        f'Added "{__CONFIG_PATH}" to "./{prettier_ignore_path}"'
    )


def __get_expected_content(
    config: dict, section: str, *, extend: bool = False
) -> Any:
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


def __get_config(path: str) -> dict:
    with open(path) as stream:
        return json.load(stream)


def __write_config(config: dict) -> None:
    with open(__CONFIG_PATH, "w") as stream:
        json.dump(config, stream, indent=4, ensure_ascii=False)
        stream.write("\n")
