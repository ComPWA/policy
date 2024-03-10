"""Configuration for working with TOML files."""

from __future__ import annotations

import shutil
from glob import glob
from pathlib import Path

import tomlkit
from ruamel.yaml import YAML

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, vscode
from compwa_policy.utilities.executor import executor
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.pyproject import PyprojectTOML
from compwa_policy.utilities.toml import to_toml_array

__INCORRECT_TAPLO_CONFIG_PATHS = [
    Path("taplo.toml"),
]


def main() -> None:
    trigger_files = [
        CONFIG_PATH.pyproject,
        CONFIG_PATH.taplo,
        *__INCORRECT_TAPLO_CONFIG_PATHS,
    ]
    if not any(f.exists() for f in trigger_files):
        return
    with executor() as do:
        do(_rename_taplo_config)
        do(_update_taplo_config)
        do(_update_precommit_repo)
        do(_update_tomlsort_config)
        do(_update_tomlsort_hook)
        do(_update_vscode_extensions)


def _update_tomlsort_config() -> None:
    pyproject = PyprojectTOML.load()
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
    tool_table = pyproject.get_table("tool", create=True)
    if tool_table.get("tomlsort") == expected_config:
        return
    tool_table["tomlsort"] = expected_config
    pyproject.modifications.append("Updated toml-sort configuration")
    pyproject.finalize()


def _update_tomlsort_hook() -> None:
    expected_hook = Repo(
        repo="https://github.com/pappasam/toml-sort",
        rev="",
        hooks=[Hook(id="toml-sort", args=YAML(typ="rt").load("[--in-place]"))],
    )
    excludes = []
    if glob("labels/*.toml"):
        excludes.append(r"labels/.*\.toml")
    if glob("labels*.toml"):
        excludes.append(r"labels.*\.toml")
    if any(glob(f"**/{f}.toml", recursive=True) for f in ("Manifest", "Project")):
        excludes.append(r".*(Manifest|Project)\.toml")
    if excludes:
        excludes = sorted(excludes, key=str.lower)
        expected_hook["hooks"][0]["exclude"] = "(?x)^(" + "|".join(excludes) + ")$"
    update_single_hook_precommit_repo(expected_hook)


def _rename_taplo_config() -> None:
    for path in __INCORRECT_TAPLO_CONFIG_PATHS:
        if not path.exists():
            continue
        shutil.move(path, CONFIG_PATH.taplo)
        msg = f"Renamed {path} to {CONFIG_PATH.taplo}"
        raise PrecommitError(msg)


def _update_taplo_config() -> None:
    template_path = COMPWA_POLICY_DIR / ".template" / CONFIG_PATH.taplo
    if not CONFIG_PATH.taplo.exists():
        shutil.copyfile(template_path, CONFIG_PATH.taplo)
        msg = f"Added {CONFIG_PATH.taplo} config for TOML formatting"
        raise PrecommitError(msg)
    with open(template_path) as f:
        expected = tomlkit.load(f)
    excludes: list[str] = [p for p in expected["exclude"] if glob(p, recursive=True)]  # type: ignore[union-attr]
    if excludes:
        excludes = sorted(excludes, key=str.lower)
        expected["exclude"] = to_toml_array(excludes, enforce_multiline=True)
    else:
        del expected["exclude"]
    with open(CONFIG_PATH.taplo) as f:
        existing = tomlkit.load(f)
    expected_str = tomlkit.dumps(expected, sort_keys=True)
    existing_str = tomlkit.dumps(existing)
    if existing_str.strip() != expected_str.strip():
        with open(CONFIG_PATH.taplo, "w") as stream:
            stream.write(expected_str)
        msg = f"Updated {CONFIG_PATH.taplo} config file"
        raise PrecommitError(msg)


def _update_precommit_repo() -> None:
    expected_hook = Repo(
        repo="https://github.com/ComPWA/mirrors-taplo",
        rev="",
        hooks=[Hook(id="taplo")],
    )
    update_single_hook_precommit_repo(expected_hook)


def _update_vscode_extensions() -> None:
    # cspell:ignore bungcip tamasfe
    with executor() as do:
        do(vscode.add_extension_recommendation, "tamasfe.even-better-toml")
        do(vscode.remove_extension_recommendation, "bungcip.better-toml", unwanted=True)
