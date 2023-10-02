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
from repoma.utilities.pyproject import (
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)

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
    executor(_update_tomlsort_config)
    executor(_update_tomlsort_hook)
    executor(_update_vscode_extensions)
    executor.finalize()


def _update_tomlsort_config() -> None:
    # cspell:ignore tomlsort
    pyproject = load_pyproject()
    sort_first = [
        "build-system",
        "project",
        "tool.setuptools",
        "tool.setuptools_scm",
    ]
    expected_config = dict(
        all=False,
        ignore_case=True,
        in_place=True,
        sort_first=to_toml_array(sort_first),
        sort_table_keys=True,
        spaces_indent_inline_array=4,
        trailing_comma_inline_array=True,
    )
    tool_table = get_sub_table(pyproject, "tool", create=True)
    if tool_table.get("tomlsort") == expected_config:
        return
    tool_table["tomlsort"] = expected_config
    write_pyproject(pyproject)
    msg = "Updated toml-sort configuration"
    raise PrecommitError(msg)


def _update_tomlsort_hook() -> None:
    expected_hook = CommentedMap(
        repo="https://github.com/pappasam/toml-sort",
        hooks=[CommentedMap(id="toml-sort", args=["--in-place"])],
    )
    excludes = ["labels.toml", "labels-physics.toml"]
    excludes = [f for f in excludes if os.path.exists(f)]
    if excludes:
        expected_hook["hooks"][0]["exclude"] = "(?x)^(" + "|".join(excludes) + ")$"
    update_single_hook_precommit_repo(expected_hook)


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
    executor(
        vscode.remove_extension_recommendation, "bungcip.better-toml", unwanted=True
    )
    executor.finalize()
