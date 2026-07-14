"""Configuration for working with TOML files."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import rtoml
import tomlkit

from compwa_policy.utilities import (
    COMPWA_POLICY_DIR,
    CONFIG_PATH,
    remove_configs,
    vscode,
)
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.match import filter_patterns
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject.getters import has_sub_table
from compwa_policy.utilities.toml import to_toml_array
from compwa_policy.utilities.yaml import read_preserved_yaml

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.session import Changelog, Session

__INCORRECT_TAPLO_CONFIG_PATHS = [Path("taplo.toml")]
__TOMBI_CONFIG_PATHS = [Path(".tombi.toml"), Path("tombi.toml")]
__POLICY_SCHEMA_PATH = "compwa-policy.schema.json"


@check_hook(
    group="format",
    paths=[
        CONFIG_PATH.pixi_toml,
        CONFIG_PATH.precommit,
        CONFIG_PATH.pyproject,
        CONFIG_PATH.taplo,
        CONFIG_PATH.vscode_extensions,
        *__INCORRECT_TAPLO_CONFIG_PATHS,
        *__TOMBI_CONFIG_PATHS,
    ],
)
def check(session: Session, args: Arguments, _ctx: CheckContext) -> None:
    trigger_files = [
        CONFIG_PATH.pyproject,
        CONFIG_PATH.taplo,
        *__INCORRECT_TAPLO_CONFIG_PATHS,
        *__TOMBI_CONFIG_PATHS,
    ]
    if not any(f.exists() for f in trigger_files):
        return
    precommit = session.precommit
    if args.toml_formatter == "taplo":
        session.changelog += _rename_taplo_config()
        _update_taplo_config(session)
        _rename_precommit_url(precommit)
        _update_precommit_repo(precommit)
        _update_tomlsort_config(session)
        _update_tomlsort_hook(precommit)
        _update_vscode_extensions(session)
        _remove_tombi_hook_and_config(session, precommit)
    elif args.toml_formatter == "tombi":
        _remove_taplo_hook_and_config(session, precommit)
        _remove_tomlsort_hook_and_config(session, precommit)
        _add_tombi_hook_and_config(
            session,
            precommit,
            errors_on_warnings=args.tombi_errors_on_warnings,
        )
        _update_tombi_vscode_extensions(session)
    else:
        msg = f"Unknown TOML formatter: {args.toml_formatter}"
        raise ValueError(msg)


def _remove_taplo_hook_and_config(
    session: Session, precommit: ModifiablePrecommit
) -> None:
    for hook_id in ["taplo", "taplo-format"]:
        precommit.remove_hook(hook_id)
    remove_configs(
        session,
        [str(CONFIG_PATH.taplo), *(str(p) for p in __INCORRECT_TAPLO_CONFIG_PATHS)],
    )


def _remove_tomlsort_hook_and_config(
    session: Session, precommit: ModifiablePrecommit
) -> None:
    precommit.remove_hook("toml-sort")
    pyproject = session.pyproject
    if pyproject is None:
        return
    tool = pyproject.get_table("tool", fallback={})
    if "tomlsort" in tool:
        del tool["tomlsort"]
        pyproject.changelog.append("Removed toml-sort configuration")


def _remove_tombi_hook_and_config(
    session: Session, precommit: ModifiablePrecommit
) -> None:
    for hook_id in ["tombi-format", "tombi-lint"]:
        precommit.remove_hook(hook_id)
    remove_configs(session, [str(path) for path in __TOMBI_CONFIG_PATHS])
    pyproject = session.pyproject
    if pyproject is None:
        return
    tool = pyproject.get_table("tool", fallback={})
    if "tombi" in tool:
        del tool["tombi"]
        pyproject.changelog.append("Removed Tombi configuration")


def _add_tombi_hook_and_config(
    session: Session,
    precommit: ModifiablePrecommit,
    *,
    errors_on_warnings: bool = False,
) -> None:
    lint_hook = Hook(id="tombi-lint")
    if errors_on_warnings:
        lint_hook["args"] = read_preserved_yaml("[--error-on-warnings]")
    expected_hook = Repo(
        repo="https://github.com/tombi-toml/tombi-pre-commit",
        rev="",
        hooks=[Hook(id="tombi-format"), lint_hook],
    )
    precommit.update_single_hook_repo(expected_hook)
    remove_configs(session, [str(path) for path in __TOMBI_CONFIG_PATHS])
    pyproject = session.pyproject
    if pyproject is None:
        return
    excludes = filter_patterns([
        "**/Cargo.toml",
        "**/Manifest.toml",
        "**/Project.toml",
        "labels*.toml",
        "labels/*.toml",
    ])
    expected = {
        "files": {},
        "format": {"rules": {"indent-width": 4, "line-width": 88}},
    }
    schema_path = _get_policy_schema_path(precommit)
    if schema_path is not None:
        expected["schemas"] = [
            {
                "root": "tool.compwa.policy",
                "path": schema_path,
                "include": ["pyproject.toml"],
            }
        ]
    if excludes:
        expected["files"]["exclude"] = to_toml_array(
            sorted(excludes, key=str.lower), multiline=True
        )
    tool = pyproject.get_table("tool", create=True)
    if tool.get("tombi") == expected:
        return
    tool["tombi"] = expected
    pyproject.changelog.append("Updated Tombi configuration")


def _get_policy_schema_path(precommit: ModifiablePrecommit) -> str | None:
    policy_repo = precommit.find_repo(r"github\.com/ComPWA/policy/?$")
    if policy_repo is not None and policy_repo.get("rev"):
        revision = policy_repo["rev"]
        return (
            f"https://raw.githubusercontent.com/ComPWA/policy/{revision}/"
            f"{__POLICY_SCHEMA_PATH}"
        )
    if Path(__POLICY_SCHEMA_PATH).exists():
        return __POLICY_SCHEMA_PATH
    return None


def _update_tomlsort_config(session: Session, /) -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    sort_first = [
        "build-system",
        "project",
        "tool.setuptools",
        "tool.setuptools_scm",
        "tool.tox.env_run_base",
    ]
    pyproject = session.pyproject
    if pyproject is None:
        return
    sort_first = [table for table in sort_first if pyproject.has_table(table)]
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
    tool_table = pyproject.get_table("tool", create=True)
    if tool_table.get("tomlsort") == expected_config:
        return
    tool_table["tomlsort"] = expected_config
    pyproject.changelog.append("Updated toml-sort configuration")


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


def _update_taplo_config(session: Session, /) -> None:
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
    pyproject = session.pyproject
    if pyproject is not None:
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
        session.changelog.append(msg)
        return
    with open(CONFIG_PATH.taplo) as f:
        existing = tomlkit.load(f)
    existing_str = tomlkit.dumps(existing, sort_keys=True)
    if existing_str.strip() != expected_str.strip():
        with open(CONFIG_PATH.taplo, "w") as stream:
            stream.write(expected_str)
        msg = f"Updated {CONFIG_PATH.taplo} config file"
        session.changelog.append(msg)


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


def _update_vscode_extensions(session: Session, /) -> None:
    # cspell:ignore bungcip tamasfe
    vscode.add_extension_recommendation(session, "tamasfe.even-better-toml")
    vscode.remove_extension_recommendation(
        session, "bungcip.better-toml", unwanted=True
    )
    vscode.remove_extension_recommendation(session, "tombi-toml.tombi")


def _update_tombi_vscode_extensions(session: Session, /) -> None:
    vscode.add_extension_recommendation(session, "tombi-toml.tombi")
    vscode.remove_extension_recommendation(
        session, "tamasfe.even-better-toml", unwanted=True
    )


def _to_regex(glob: str) -> str:
    r"""Convert glob pattern to regex.

    >>> _to_regex("**/*.toml")
    '.*/.*\\.toml'
    """
    return glob.replace("**", "*").replace(".", r"\.").replace("*", r".*")
