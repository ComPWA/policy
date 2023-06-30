"""Configuration for working with TOML files."""

import os
import shutil
from pathlib import Path
from typing import List, Union

from ruamel.yaml.comments import CommentedMap

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, vscode
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import update_single_hook_precommit_repo

__INCORRECT_TAPLO_CONFIG_PATHS = [
    "taplo.toml",
]
__TRIGGER_FILES: List[Union[Path, str]] = [
    "pyproject.toml",
    CONFIG_PATH.taplo,
    *__INCORRECT_TAPLO_CONFIG_PATHS,
]


def main() -> None:
    if not any(os.path.exists(f) for f in __TRIGGER_FILES):
        return
    executor = Executor()
    executor(_rename_taplo_config)
    executor(_update_taplo_config)
    executor(_update_precommit_repo)
    executor(_update_vscode_extensions)
    executor.finalize()


def _rename_taplo_config() -> None:
    for path in __INCORRECT_TAPLO_CONFIG_PATHS:
        if not os.path.exists(path):
            continue
        shutil.move(path, CONFIG_PATH.taplo)
        msg = f"Renamed {path} to {CONFIG_PATH.taplo}"
        raise PrecommitError(msg)


def _update_taplo_config() -> None:
    template_path = REPOMA_DIR / ".template" / CONFIG_PATH.taplo
    if not CONFIG_PATH.taplo.exists():
        shutil.copyfile(template_path, CONFIG_PATH.taplo)
        msg = f"Added {CONFIG_PATH.taplo} config for TOML formatting"
        raise PrecommitError(msg)
    with open(template_path) as f:
        expected_content = f.read()
    with open(CONFIG_PATH.taplo) as f:
        existing_content = f.read()
    if existing_content != expected_content:
        with open(CONFIG_PATH.taplo, "w") as stream:
            stream.write(expected_content)
        msg = f"Updated {CONFIG_PATH.taplo} config file"
        raise PrecommitError(msg)


def _update_precommit_repo() -> None:
    expected_hook = CommentedMap(
        repo="https://github.com/ComPWA/mirrors-taplo",
        hooks=[CommentedMap(id="taplo")],
    )
    update_single_hook_precommit_repo(expected_hook)


def _update_vscode_extensions() -> None:
    # cspell:ignore bungcip tamasfe
    executor = Executor()
    executor(vscode.add_extension_recommendation, "tamasfe.even-better-toml")
    executor(vscode.remove_extension_recommendation, "bungcip.better-toml")
    executor.finalize()
