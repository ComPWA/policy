"""Check the configuration for `Prettier <https://prettier.io>`_."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterable

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.readme import add_badge, remove_badge

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import Precommit

# cspell:ignore esbenp rettier
__VSCODE_EXTENSION_NAME = "esbenp.prettier-vscode"
__BADGE = """
[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)
""".strip()
__BADGE_PATTERN = r"\[\!\[[Pp]rettier.*\]\(.*prettier.*\)\]\(.*prettier.*\)\n?"


with open(COMPWA_POLICY_DIR / ".template" / CONFIG_PATH.prettier) as __STREAM:
    __EXPECTED_CONFIG = __STREAM.read()


def main(precommit: Precommit, no_prettierrc: bool) -> None:
    if precommit.find_repo(r".*/mirrors-prettier") is None:
        _remove_configuration()
    else:
        with Executor() as do:
            do(_fix_config_content, no_prettierrc)
            do(add_badge, __BADGE)
            do(vscode.add_extension_recommendation, __VSCODE_EXTENSION_NAME)
            do(_update_prettier_ignore)


def _remove_configuration() -> None:
    if CONFIG_PATH.prettier.exists():
        os.remove(CONFIG_PATH.prettier)
        msg = f'"{CONFIG_PATH.prettier}" is no longer required and has been removed'
        raise PrecommitError(msg)
    remove_badge(__BADGE_PATTERN)
    vscode.remove_extension_recommendation(__VSCODE_EXTENSION_NAME)


def _fix_config_content(no_prettierrc: bool) -> None:
    if no_prettierrc:
        with Executor() as do:
            do(__remove_prettierrc)
            do(vscode.remove_settings, {"[markdown]": {"editor.wordWrap"}})
    else:
        if not CONFIG_PATH.prettier.exists():
            existing_content = ""
        else:
            with open(CONFIG_PATH.prettier) as stream:
                existing_content = stream.read()
        if existing_content != __EXPECTED_CONFIG:
            with open(CONFIG_PATH.prettier, "w") as stream:
                stream.write(__EXPECTED_CONFIG)
            msg = f"Updated {CONFIG_PATH.prettier} config file"
            raise PrecommitError(msg)

    wrong_config_paths = [  # https://prettier.io/docs/en/configuration.html
        ".prettierrc.json",
        ".prettierrc.yml",
        ".prettierrc.yaml",
        ".prettierrc.json5",
        ".prettierrc.toml",
    ]
    for path in wrong_config_paths:
        if os.path.exists(path):
            os.remove(path)
            msg = f'Removed "{path}": "{CONFIG_PATH.prettier}" should suffice'
            raise PrecommitError(msg)


def __remove_prettierrc() -> None:
    if not CONFIG_PATH.prettier.exists():
        return
    CONFIG_PATH.prettier.unlink()
    msg = f"Removed {CONFIG_PATH.prettier} as requested by --no-prettierrc"
    raise PrecommitError(msg)


def _update_prettier_ignore() -> None:
    __remove_forbidden_paths()
    __insert_expected_paths()


def __remove_forbidden_paths() -> None:
    if not os.path.exists(CONFIG_PATH.prettier_ignore):
        return
    existing = __get_existing_lines()
    forbidden = {
        ".cspell.json",
        "cspell.config.yaml",
        "cspell.json",
    }
    expected = [
        s for s in existing if s.split("#", maxsplit=1)[0].strip() not in forbidden
    ]
    if existing != expected:
        __write_lines(expected)
        msg = f"Removed forbidden paths from {CONFIG_PATH.prettier_ignore}"
        raise PrecommitError(msg)


def __insert_expected_paths() -> None:
    existing = __get_existing_lines()
    obligatory = [
        "LICENSE",
    ]
    obligatory = [p for p in obligatory if os.path.exists(p)]
    expected = [*sorted(set(existing + obligatory) - {""}), ""]
    if expected == [""] and os.path.exists(CONFIG_PATH.prettier_ignore):
        os.remove(CONFIG_PATH.prettier_ignore)
        msg = f"{CONFIG_PATH.prettier_ignore} is not needed"
        raise PrecommitError(msg)
    if existing != expected:
        __write_lines(expected)
        msg = f"Added paths to {CONFIG_PATH.prettier_ignore}"
        raise PrecommitError(msg)


def __get_existing_lines() -> list[str]:
    if not os.path.exists(CONFIG_PATH.prettier_ignore):
        return [""]
    with open(CONFIG_PATH.prettier_ignore) as f:
        return f.read().split("\n")


def __write_lines(lines: Iterable[str]) -> None:
    content = "\n".join(sorted(set(lines) - {""})) + "\n"
    with open(CONFIG_PATH.prettier_ignore, "w") as f:
        f.write(content)
