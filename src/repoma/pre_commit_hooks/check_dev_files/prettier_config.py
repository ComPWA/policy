"""Check the configuration for `Prettier <https://prettier.io>`_."""

import os

from repoma._utilities import (
    CONFIG_PATH,
    REPOMA_DIR,
    add_badge,
    add_vscode_extension_recommendation,
    find_precommit_hook,
    remove_badge,
    remove_vscode_extension_recommendation,
)
from repoma.pre_commit_hooks.errors import PrecommitError

# cspell:ignore esbenp
__VSCODE_EXTENSION_NAME = "esbenp.prettier-vscode"

# pylint: disable=line-too-long
__BADGE = "[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)"
__BADGE_PATTERN = r"\[\!\[[Pp]rettier.*\]\(.*prettier.*\)\]\(.*prettier.*\)\n?"


with open(f"{REPOMA_DIR}/{CONFIG_PATH.prettier}") as __STREAM:
    __EXPECTED_CONFIG = __STREAM.read()


def fix_prettier_config(no_prettierrc: bool) -> None:
    precommit_hook = find_precommit_hook(r".*/mirrors-prettier")
    if precommit_hook is None:
        _remove_configuration()
    else:
        _fix_config_content(no_prettierrc)
        add_badge(__BADGE)
        add_vscode_extension_recommendation(__VSCODE_EXTENSION_NAME)


def _remove_configuration() -> None:
    if os.path.exists(CONFIG_PATH.prettier):
        os.remove(CONFIG_PATH.prettier)
        raise PrecommitError(
            f'"{CONFIG_PATH.prettier}" is no longer required'
            " and has been removed"
        )
    remove_badge(__BADGE_PATTERN)
    remove_vscode_extension_recommendation(__VSCODE_EXTENSION_NAME)


def _fix_config_content(no_prettierrc: bool) -> None:
    if no_prettierrc:
        if os.path.exists(CONFIG_PATH.prettier):
            os.remove(CONFIG_PATH.prettier)
            raise PrecommitError(
                f'Removed "./{CONFIG_PATH.prettier}" as requested by --no-prettierrc'
            )
    else:
        if not os.path.exists(CONFIG_PATH.prettier):
            existing_content = ""
        else:
            with open(CONFIG_PATH.prettier, "r") as stream:
                existing_content = stream.read()
        if existing_content != __EXPECTED_CONFIG:
            with open(CONFIG_PATH.prettier, "w") as stream:
                stream.write(__EXPECTED_CONFIG)
            raise PrecommitError(
                f'Updated "./{CONFIG_PATH.prettier}" config file'
            )

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
            raise PrecommitError(
                f'Removed "{path}": "{CONFIG_PATH.prettier}" should suffice'
            )
