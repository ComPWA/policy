"""Check the configuration for `Prettier <https://prettier.io>`_."""

import os
from typing import Iterable, List

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import PrecommitConfig
from repoma.utilities.readme import add_badge, remove_badge
from repoma.utilities.vscode import (
    add_vscode_extension_recommendation,
    remove_vscode_extension_recommendation,
)

# cspell:ignore esbenp rettier
__VSCODE_EXTENSION_NAME = "esbenp.prettier-vscode"

# pylint: disable=line-too-long
# fmt: off
__BADGE = "[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)"
# fmt: on
__BADGE_PATTERN = r"\[\!\[[Pp]rettier.*\]\(.*prettier.*\)\]\(.*prettier.*\)\n?"


with open(REPOMA_DIR / ".template" / CONFIG_PATH.prettier) as __STREAM:
    __EXPECTED_CONFIG = __STREAM.read()


def main(no_prettierrc: bool) -> None:
    config = PrecommitConfig.load()
    repo = config.find_repo(r".*/mirrors-prettier")
    if repo is None:
        _remove_configuration()
    else:
        executor = Executor()
        executor(_fix_config_content, no_prettierrc)
        executor(add_badge, __BADGE)
        executor(add_vscode_extension_recommendation, __VSCODE_EXTENSION_NAME)
        executor(_update_prettier_ignore)
        if executor.error_messages:
            raise PrecommitError(executor.merge_messages())


def _remove_configuration() -> None:
    if CONFIG_PATH.prettier.exists():
        os.remove(CONFIG_PATH.prettier)
        raise PrecommitError(
            f'"{CONFIG_PATH.prettier}" is no longer required and has been removed'
        )
    remove_badge(__BADGE_PATTERN)
    remove_vscode_extension_recommendation(__VSCODE_EXTENSION_NAME)


def _fix_config_content(no_prettierrc: bool) -> None:
    if no_prettierrc:
        if CONFIG_PATH.prettier.exists():
            os.remove(CONFIG_PATH.prettier)
            raise PrecommitError(
                f"Removed {CONFIG_PATH.prettier} as requested by --no-prettierrc"
            )
    else:
        if not CONFIG_PATH.prettier.exists():
            existing_content = ""
        else:
            with open(CONFIG_PATH.prettier) as stream:
                existing_content = stream.read()
        if existing_content != __EXPECTED_CONFIG:
            with open(CONFIG_PATH.prettier, "w") as stream:
                stream.write(__EXPECTED_CONFIG)
            raise PrecommitError(f"Updated {CONFIG_PATH.prettier} config file")

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
        raise PrecommitError(
            f"Removed forbidden paths from {CONFIG_PATH.prettier_ignore}"
        )


def __insert_expected_paths() -> None:
    existing = __get_existing_lines()
    obligatory = [
        "LICENSE",
    ]
    obligatory = [p for p in obligatory if os.path.exists(p)]
    expected = sorted(set(existing + obligatory) - {""}) + [""]
    if expected == [""] and os.path.exists(CONFIG_PATH.prettier_ignore):
        os.remove(CONFIG_PATH.prettier_ignore)
        raise PrecommitError(f"{CONFIG_PATH.prettier_ignore} is not needed")
    if existing != expected:
        __write_lines(expected)
        raise PrecommitError(f"Added paths to {CONFIG_PATH.prettier_ignore}")


def __get_existing_lines() -> List[str]:
    if not os.path.exists(CONFIG_PATH.prettier_ignore):
        return [""]
    with open(CONFIG_PATH.prettier_ignore) as f:
        return f.read().split("\n")


def __write_lines(lines: Iterable[str]) -> None:
    content = "\n".join(sorted(set(lines) - {""})) + "\n"
    with open(CONFIG_PATH.prettier_ignore, "w") as f:
        f.write(content)
