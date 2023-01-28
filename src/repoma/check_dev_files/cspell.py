"""Check the configuration for cspell.

See `cSpell
<https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell>`_.
"""

import json
import os
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Union

import yaml

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, rename_file
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    PrecommitConfig,
    Repo,
    fromdict,
    load_round_trip_precommit_config,
)
from repoma.utilities.readme import add_badge, remove_badge
from repoma.utilities.vscode import (
    add_vscode_extension_recommendation,
    remove_vscode_extension_recommendation,
)

__VSCODE_EXTENSION_NAME = "streetsidesoftware.code-spell-checker"

# cspell:ignore pelling
# pylint: disable=line-too-long
# fmt: off
__BADGE = (
    "[![Spelling"
    " checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell)"
)
# fmt: on
__BADGE_PATTERN = r"\[\!\[[Ss]pelling.*\]\(.*cspell.*\)\]\(.*cspell.*\)\n?"
__REPO_URL = "https://github.com/streetsidesoftware/cspell-cli"


with open(REPOMA_DIR / ".template" / CONFIG_PATH.cspell) as __STREAM:
    __EXPECTED_CONFIG = json.load(__STREAM)


def main() -> None:
    rename_file("cspell.json", str(CONFIG_PATH.cspell))
    executor = Executor()
    executor(_update_cspell_repo_url)
    config = PrecommitConfig.load()
    repo = config.find_repo(__REPO_URL)
    if repo is None:
        executor(_remove_configuration)
    else:
        executor(_check_check_hook_options)
        executor(_fix_config_content)
        executor(_sort_config_entries)
        executor(add_badge, __BADGE)
        executor(add_vscode_extension_recommendation, __VSCODE_EXTENSION_NAME)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _update_cspell_repo_url(path: Path = CONFIG_PATH.precommit) -> None:
    old_url_patters = [
        r".*/mirrors-cspell(.git)?$",
    ]
    config = PrecommitConfig.load(path)
    for pattern in old_url_patters:
        repo_index = config.get_repo_index(pattern)
        if repo_index is None:
            continue
        config_dict, yaml_parser = load_round_trip_precommit_config(path)
        config_dict["repos"][repo_index]["repo"] = __REPO_URL
        yaml_parser.dump(config_dict, path)
        raise PrecommitError(
            f"Updated cSpell pre-commit repo URL to {__REPO_URL} in {path}"
        )


def _remove_configuration() -> None:
    if CONFIG_PATH.cspell.exists():
        os.remove(CONFIG_PATH.cspell)
        raise PrecommitError(
            f'"{CONFIG_PATH.cspell}" is no longer required and has been removed'
        )
    if CONFIG_PATH.editor_config.exists():
        with open(CONFIG_PATH.editor_config) as stream:
            prettier_ignore_content = stream.readlines()
        expected_line = str(CONFIG_PATH.cspell) + "\n"
        if expected_line in set(prettier_ignore_content):
            prettier_ignore_content.remove(expected_line)
            with open(CONFIG_PATH.editor_config, "w") as stream:
                stream.writelines(prettier_ignore_content)
            raise PrecommitError(
                f'"{CONFIG_PATH.cspell}" in {CONFIG_PATH.editor_config}'
                " is no longer required and has been removed"
            )
    executor = Executor()
    executor(remove_badge, __BADGE_PATTERN)
    executor(remove_vscode_extension_recommendation, __VSCODE_EXTENSION_NAME)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _check_check_hook_options() -> None:
    config = PrecommitConfig.load()
    existing = config.find_repo(__REPO_URL)
    if existing is None:
        raise PrecommitError(f"{CONFIG_PATH.precommit} is missing a repo: {__REPO_URL}")
    expected_yaml = f"""
  - repo: {__REPO_URL}
    rev: ...
    hooks:
      - id: cspell
    """
    expected = fromdict(yaml.safe_load(expected_yaml)[0], Repo)
    existing.rev = expected.rev
    if existing != expected:
        raise PrecommitError(
            "cSpell pre-commit hook should have the following form:\n" + expected_yaml
        )


def _fix_config_content() -> None:
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
        if not extend:
            return __sort_section(expected_section_content, section)
        expected_section_content_set = set(expected_section_content)
        expected_section_content_set.update(section_content)
        return __sort_section(expected_section_content_set, section)
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


def __get_config(path: Union[str, Path]) -> dict:
    with open(path) as stream:
        return json.load(stream)


def __write_config(config: dict) -> None:
    with open(CONFIG_PATH.cspell, "w") as stream:
        json.dump(config, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def __sort_section(content: Iterable[Any], section_name: str) -> List[str]:
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
    return sorted(content, key=lambda s: s.lower() if isinstance(s, str) else s)
