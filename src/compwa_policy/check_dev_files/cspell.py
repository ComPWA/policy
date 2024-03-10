"""Check the configuration for cspell.

See `cSpell
<https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell>`_.
"""

from __future__ import annotations

import json
import os
from glob import glob
from typing import TYPE_CHECKING, Any, Iterable, Sequence

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, rename_file, vscode
from compwa_policy.utilities.executor import executor
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    find_repo,
    load_precommit_config,
    load_roundtrip_precommit_config,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.readme import add_badge, remove_badge

if TYPE_CHECKING:
    from pathlib import Path

__VSCODE_EXTENSION_NAME = "streetsidesoftware.code-spell-checker"

# cspell:ignore pelling
# fmt: off
__BADGE = (
    "[![Spelling"
    " checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell)"
)
# fmt: on
__BADGE_PATTERN = r"\[\!\[[Ss]pelling.*\]\(.*cspell.*\)\]\(.*cspell.*\)\n?"
__REPO_URL = "https://github.com/streetsidesoftware/cspell-cli"


with open(COMPWA_POLICY_DIR / ".template" / CONFIG_PATH.cspell) as __STREAM:
    __EXPECTED_CONFIG = json.load(__STREAM)


def main(no_cspell_update: bool) -> None:
    rename_file("cspell.json", str(CONFIG_PATH.cspell))
    with executor() as do:
        do(_update_cspell_repo_url)
        has_cspell_hook = False
        if CONFIG_PATH.cspell.exists():
            config = load_precommit_config()
            has_cspell_hook = find_repo(config, __REPO_URL) is not None
        if not has_cspell_hook:
            do(_remove_configuration)
        else:
            do(_update_precommit_repo)
            if not no_cspell_update:
                do(_update_config_content)
            do(_sort_config_entries)
            do(add_badge, __BADGE)
            do(vscode.add_extension_recommendation, __VSCODE_EXTENSION_NAME)


def _update_cspell_repo_url(path: Path = CONFIG_PATH.precommit) -> None:
    old_url_patters = [
        r".*/mirrors-cspell(.git)?$",
    ]
    config, yaml = load_roundtrip_precommit_config(path)
    for pattern in old_url_patters:
        repo = find_repo(config, pattern)
        if repo is None:
            continue
        repo["repo"] = __REPO_URL
        yaml.dump(config, path)
        msg = f"Updated cSpell pre-commit repo URL to {__REPO_URL} in {path}"
        raise PrecommitError(msg)


def _remove_configuration() -> None:
    if CONFIG_PATH.cspell.exists():
        os.remove(CONFIG_PATH.cspell)
        msg = f'"{CONFIG_PATH.cspell}" is no longer required and has been removed'
        raise PrecommitError(msg)
    if CONFIG_PATH.editorconfig.exists():
        with open(CONFIG_PATH.editorconfig) as stream:
            prettier_ignore_content = stream.readlines()
        expected_line = str(CONFIG_PATH.cspell) + "\n"
        if expected_line in set(prettier_ignore_content):
            prettier_ignore_content.remove(expected_line)
            with open(CONFIG_PATH.editorconfig, "w") as stream:
                stream.writelines(prettier_ignore_content)
            msg = (
                f'"{CONFIG_PATH.cspell}" in {CONFIG_PATH.editorconfig} is no longer'
                " required and has been removed"
            )
            raise PrecommitError(msg)
    with executor() as do:
        do(remove_badge, __BADGE_PATTERN)
        do(vscode.remove_extension_recommendation, __VSCODE_EXTENSION_NAME)


def _update_precommit_repo() -> None:
    expected_hook = Repo(
        repo=__REPO_URL,
        rev="",
        hooks=[Hook(id="cspell")],
    )
    update_single_hook_precommit_repo(expected_hook)


def _update_config_content() -> None:
    if not CONFIG_PATH.cspell.exists():
        with open(CONFIG_PATH.cspell, "w") as stream:
            stream.write("{}")
    config = __get_config(CONFIG_PATH.cspell)
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
        error_message += f" in {CONFIG_PATH.cspell} has been updated."
        raise PrecommitError(error_message)


def _sort_config_entries() -> None:
    config = __get_config(CONFIG_PATH.cspell)
    error_message = ""
    fixed_sections = []
    for section, section_content in config.items():
        if not isinstance(section_content, list):
            continue
        sorted_section_content = __sort_section(section_content, section)
        if section_content == sorted_section_content:
            continue
        fixed_sections.append('"' + section + '"')
        config[section] = sorted_section_content
    if fixed_sections:
        __write_config(config)
        error_message = __express_list_of_sections(fixed_sections)
        error_message += f" in {CONFIG_PATH.cspell} has been sorted alphabetically."
        raise PrecommitError(error_message)


def __get_expected_content(config: dict, section: str, *, extend: bool = False) -> Any:
    if section not in config:
        return __EXPECTED_CONFIG[section]
    section_content = config[section]
    if section not in __EXPECTED_CONFIG:
        return section_content
    expected_section_content = __EXPECTED_CONFIG[section]
    if isinstance(expected_section_content, str):
        return expected_section_content
    if isinstance(expected_section_content, list):
        if section == "ignorePaths":
            expected_section_content = [
                p for p in expected_section_content if glob(p, recursive=True)
            ]
        if not extend:
            return __sort_section(expected_section_content, section)
        expected_section_content_set = set(expected_section_content)
        expected_section_content_set.update(section_content)
        return __sort_section(expected_section_content_set, section)
    msg = (
        "No implementation for section content of type"
        f' {section_content.__class__.__name__} (section: "{section}"'
    )
    raise NotImplementedError(msg)


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
        if len(sections) > 2:  # noqa: PLR2004
            sentence += ","
        sentence += " and " + sections[-1]
    return sentence


def __get_config(path: str | Path) -> dict:
    with open(path) as stream:
        return json.load(stream)


def __write_config(config: dict) -> None:
    with open(CONFIG_PATH.cspell, "w") as stream:
        json.dump(config, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def __sort_section(content: Iterable[Any], section_name: str) -> list[str]:
    """Sort a list section.

    >>> __sort_section({"one", "Two"}, section_name="words")
    ['one', 'Two']
    >>> __sort_section({"one", "Two"}, section_name="ignoreWords")
    ['Two', 'one']
    """
    if section_name == "dictionaryDefinitions":

        def sort_key(value: Any) -> str:
            name = value.get("name", "")
            return name.lower()

        return sorted(content, key=sort_key)
    if section_name == "ignoreWords":
        return sorted(content)
    return vscode.sort_case_insensitive(content)
