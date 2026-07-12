"""Configuration for working with TOML files."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import rtoml
import tomlkit

from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, vscode
from compwa_policy.utilities.match import filter_patterns
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    use_modifiable_pyproject,
)
from compwa_policy.utilities.pyproject.getters import has_sub_table
from compwa_policy.utilities.toml import to_toml_array
from compwa_policy.utilities.yaml import read_preserved_yaml

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.session import Changelog, Session

__INCORRECT_TAPLO_CONFIG_PATHS = [
    Path("taplo.toml"),
]


def main(session: Session) -> None:
    trigger_files = [
        CONFIG_PATH.pyproject,
        CONFIG_PATH.taplo,
        *__INCORRECT_TAPLO_CONFIG_PATHS,
    ]
    if not any(f.exists() for f in trigger_files):
        return
    precommit = session.precommit
    session.changelog += _rename_taplo_config()
    session.changelog += _update_taplo_config()
    _rename_precommit_url(precommit)
    _update_precommit_repo(precommit)
    session.changelog += _update_tomlsort_config(session.pyproject)
    _update_tomlsort_hook(precommit)
    session.changelog += _update_vscode_extensions()


def _update_tomlsort_config(pyproject: ModifiablePyproject | None = None) -> Changelog:
    if pyproject is None and not CONFIG_PATH.pyproject.exists():
        return []
    sort_first = [
        "build-system",
        "project",
        "tool.setuptools",
        "tool.setuptools_scm",
        "tool.tox.env_run_base",
    ]
    readonly_pyproject = pyproject or Pyproject.load()
    sort_first = [table for table in sort_first if readonly_pyproject.has_table(table)]
    expected_config = dict(
        all=False,
        ignore_case=True,
        in_place=True,
        sort_first=to_toml_array(sort_first),
        spaces_indent_inline_array=4,
        trailing_comma_inline_array=True,
    )
    if not sort_first:
        expected_config.pop("sort_first")
    with use_modifiable_pyproject(pyproject) as (config, include_changelog):
        if config is None:
            return []
        tool_table = config.get_table("tool", create=True)
        if tool_table.get("tomlsort") == expected_config:
            return []
        tool_table["tomlsort"] = expected_config
        config.changelog.append("Updated toml-sort configuration")
        if include_changelog:
            return list(config.changelog)
    return []


def _update_tomlsort_hook(precommit: ModifiablePrecommit) -> None:
    expected_hook = Repo(
        repo="https://github.com/pappasam/toml-sort",
        rev="",
        hooks=[Hook(id="toml-sort", args=read_preserved_yaml("[--in-place]"))],
    )
    excludes = filter_patterns([
        "**/Manifest.toml",
        "**/Project.toml",
        "labels*.toml",
        "labels/*.toml",
    ])
    if excludes:
        regex_excludes = sorted(_to_regex(r) for r in excludes)
        expected_hook["hooks"][0]["exclude"] = (
            "(?x)^(" + "|".join(regex_excludes) + ")$"
        )
    precommit.update_single_hook_repo(expected_hook)


def _rename_taplo_config() -> Changelog:
    for path in __INCORRECT_TAPLO_CONFIG_PATHS:
        if not path.exists():
            continue
        shutil.move(path, CONFIG_PATH.taplo)
        msg = f"Renamed {path} to {CONFIG_PATH.taplo}"
        return [msg]
    return []


def _update_taplo_config() -> Changelog:
    template_path = COMPWA_POLICY_DIR / ".template" / CONFIG_PATH.taplo
    with open(template_path) as f:
        expected = tomlkit.load(f)

    excludes = filter_patterns(expected["exclude"])
    if excludes:
        sorted_excludes = sorted(excludes, key=str.lower)
        expected["exclude"] = to_toml_array(sorted_excludes, multiline=True)
    else:
        del expected["exclude"]

    rules = tomlkit.aot()
    if CONFIG_PATH.pixi_toml.exists():
        with open(CONFIG_PATH.pixi_toml) as stream:
            pixi_config = rtoml.load(stream)
        if has_sub_table(pixi_config, "tasks"):
            rules.append(__taplo_rule(CONFIG_PATH.pixi_toml, ["tasks"]))
    if CONFIG_PATH.pyproject.exists():
        pyproject = Pyproject.load()
        keys = [
            key
            for key in ["tool.pixi.tasks", "tool.poe.groups", "tool.poe.tasks"]
            if pyproject.has_table(key)
        ]
        if keys:
            rules.append(__taplo_rule(CONFIG_PATH.pyproject, keys))
    if rules:
        expected["rule"] = rules

    expected_str = tomlkit.dumps(expected, sort_keys=True).lstrip()
    if not CONFIG_PATH.taplo.exists():
        with open(CONFIG_PATH.taplo, "w") as stream:
            stream.write(expected_str)
        msg = f"Added {CONFIG_PATH.taplo} config for TOML formatting"
        return [msg]
    with open(CONFIG_PATH.taplo) as f:
        existing = tomlkit.load(f)
    existing_str = tomlkit.dumps(existing, sort_keys=True)
    if existing_str.strip() != expected_str.strip():
        with open(CONFIG_PATH.taplo, "w") as stream:
            stream.write(expected_str)
        msg = f"Updated {CONFIG_PATH.taplo} config file"
        return [msg]
    return []


def __taplo_rule(toml_path: Path | str, keys: list[str]) -> dict:
    return dict(
        include=[f"**/{toml_path}"],
        keys=to_toml_array(keys, multiline=len(keys) > 1),
        formatting=dict(reorder_arrays=False),
    )


def _rename_precommit_url(precommit: ModifiablePrecommit) -> None:
    mirrors_repo_with_idx = precommit.find_repo_with_index(r"^.*/mirrors-taplo$")
    rev = ""
    if mirrors_repo_with_idx is not None:
        idx, repo = mirrors_repo_with_idx
        rev = repo["rev"]
        precommit.document["repos"].pop(idx)
        precommit.changelog.append("Renamed mirrors-taplo repo to taplo-pre-commit")
    expected_hook = Repo(
        repo="https://github.com/ComPWA/taplo-pre-commit",
        rev=rev,
        hooks=[Hook(id="taplo-format")],
    )
    precommit.update_single_hook_repo(expected_hook)


def _update_precommit_repo(precommit: ModifiablePrecommit) -> None:
    mirrors_repo_with_idx = precommit.find_repo_with_index(r"^.*/mirrors-taplo$")
    if mirrors_repo_with_idx is not None:
        idx, _ = mirrors_repo_with_idx
        precommit.document["repos"].pop(idx)
        precommit.changelog.append("Renamed mirrors-taplo repo to taplo-pre-commit")
    expected_hook = Repo(
        repo="https://github.com/ComPWA/taplo-pre-commit",
        rev="",
        hooks=[Hook(id="taplo-format")],
    )
    precommit.update_single_hook_repo(expected_hook)


def _update_vscode_extensions() -> Changelog:
    # cspell:ignore bungcip tamasfe
    changes: Changelog = []
    changes += vscode.add_extension_recommendation("tamasfe.even-better-toml")
    changes += vscode.remove_extension_recommendation(
        "bungcip.better-toml", unwanted=True
    )
    return changes


def _to_regex(glob: str) -> str:
    r"""Convert glob pattern to regex.

    >>> _to_regex("**/*.toml")
    '.*/.*\\.toml'
    """
    return glob.replace("**", "*").replace(".", r"\.").replace("*", r".*")
