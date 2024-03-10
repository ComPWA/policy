"""Check content of :code:`.pre-commit-config.yaml` and related files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import (
    PrecommitConfig,
    Repo,
    find_repo,
    load_precommit_config,
    load_roundtrip_precommit_config,
)
from compwa_policy.utilities.pyproject import PyprojectTOML, get_constraints_file
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml


def main() -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    with Executor() as do:
        do(_sort_hooks)
        do(_update_conda_environment)
        do(_update_precommit_ci_commit_msg)
        do(_update_precommit_ci_skip)
        do(_update_repo_urls)


def _sort_hooks() -> None:
    config, yaml = load_roundtrip_precommit_config()
    repos = config.get("repos")
    if repos is None:
        return
    sorted_repos = sorted(repos, key=__repo_sort_key)
    if sorted_repos != repos:
        config["repos"] = sorted_repos
        yaml.dump(config, CONFIG_PATH.precommit)
        msg = f"Sorted pre-commit hooks in {CONFIG_PATH.precommit}"
        raise PrecommitError(msg)


def __repo_sort_key(repo: Repo) -> tuple[int, str]:
    repo_url = repo["repo"]
    if repo_url == "meta":
        return 0, "meta"
    hooks = repo["hooks"]
    if any(hook["id"] == "nbstripout" for hook in hooks):
        return 1, repo_url
    if len(hooks) > 1:
        return 2, repo_url
    hook_id = hooks[0]["id"]
    formatter_hooks = {
        "black",
        "blacken-docs",
        "isort",
        "prettier",
        "taplo",
        "toml-sort",
    }
    if hook_id in formatter_hooks:
        return 3, hook_id
    return 4, hook_id


def _update_precommit_ci_commit_msg() -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    config, yaml = load_roundtrip_precommit_config()
    precommit_ci = config.get("ci")
    if precommit_ci is None:
        return
    if __has_constraint_files():
        expected_msg = "MAINT: update pip constraints and pre-commit"
    else:
        expected_msg = "MAINT: autoupdate pre-commit hooks"
    key = "autoupdate_commit_msg"
    autoupdate_commit_msg = precommit_ci.get(key)
    if autoupdate_commit_msg != expected_msg:
        precommit_ci[key] = expected_msg  # type:ignore[literal-required]
        yaml.dump(config, CONFIG_PATH.precommit)
        msg = f"Updated ci.{key} in {CONFIG_PATH.precommit} to {expected_msg!r}"
        raise PrecommitError(msg)


def __has_constraint_files() -> bool:
    python_versions = PyprojectTOML.load().get_supported_python_versions()
    constraint_files = [get_constraints_file(v) for v in python_versions]
    constraint_paths = [Path(path) for path in constraint_files if path is not None]
    return any(path.exists() for path in constraint_paths)


def _update_precommit_ci_skip() -> None:
    config, yaml = load_roundtrip_precommit_config()
    precommit_ci = config.get("ci")
    if precommit_ci is None:
        return
    local_hooks = get_local_hooks(config)
    non_functional_hooks = get_non_functional_hooks(config)
    expected_skips = sorted(set(non_functional_hooks) | set(local_hooks))
    existing_skips = precommit_ci.get("skip")
    if not expected_skips and existing_skips is not None:
        del precommit_ci["skip"]
        yaml.dump(config, CONFIG_PATH.precommit)
        msg = f"Removed redundant ci.skip section from {CONFIG_PATH.precommit}"
        raise PrecommitError(msg)
    if existing_skips != expected_skips:
        precommit_ci["skip"] = sorted(expected_skips)
        yaml_config = cast(CommentedMap, config)
        yaml_config.yaml_set_comment_before_after_key("repos", before="\n")
        yaml.dump(yaml_config, CONFIG_PATH.precommit)
        msg = f"Updated ci.skip section in {CONFIG_PATH.precommit}"
        raise PrecommitError(msg)


def get_local_hooks(config: PrecommitConfig) -> list[str]:
    repos = config["repos"]
    return [h["id"] for r in repos for h in r["hooks"] if r["repo"] == "local"]


def get_non_functional_hooks(config: PrecommitConfig) -> list[str]:
    return [
        hook["id"]
        for repo in config["repos"]
        for hook in repo["hooks"]
        if repo["repo"]
        if hook["id"] in __get_skipped_hooks(config)
    ]


def _update_conda_environment() -> None:
    """Temporary fix for Prettier v4 alpha releases.

    https://prettier.io/blog/2023/11/30/cli-deep-dive#installation
    """
    path = Path("environment.yml")
    if not path.exists():
        return
    yaml = create_prettier_round_trip_yaml()
    conda_env: CommentedMap = yaml.load(path)
    variables: CommentedMap = conda_env.get("variables", {})
    key = "PRETTIER_LEGACY_CLI"
    precommit_config = load_precommit_config()
    if __has_prettier_v4alpha(precommit_config):
        if key not in variables:
            variables[key] = DoubleQuotedScalarString("1")
            conda_env["variables"] = variables
            yaml.dump(conda_env, path)
            msg = f"Set {key} environment variable in {path}"
            raise PrecommitError(msg)
    elif key in variables:
        del variables[key]
        if not variables:
            del conda_env["variables"]
        yaml.dump(conda_env, path)
        msg = f"Removed {key} environment variable {path}"
        raise PrecommitError(msg)


def __get_skipped_hooks(config: PrecommitConfig) -> set[str]:
    skipped_hooks = {
        "check-jsonschema",
        "pyright",
        "taplo",
    }
    if __has_prettier_v4alpha(config):
        skipped_hooks.add("prettier")
    return skipped_hooks


def __has_prettier_v4alpha(config: PrecommitConfig) -> bool:
    repo = find_repo(config, search_pattern=r"^.*/mirrors-prettier$")
    if repo is None:
        return False
    rev = repo.get("rev", "")
    return rev.startswith("v4") and "alpha" in rev


def _update_repo_urls() -> None:
    redirects = {
        r"^.*github\.com/ComPWA/repo-maintenance$": "https://github.com/ComPWA/policy",
    }
    config, yaml = load_roundtrip_precommit_config()
    repos = config["repos"]
    updated_repos: list[tuple[str, str]] = []
    for repo in repos:
        url = repo["repo"]
        for redirect, new_url in redirects.items():
            if re.match(redirect, url):
                repo["repo"] = new_url
                updated_repos.append((url, new_url))
    if updated_repos:
        yaml.dump(config, CONFIG_PATH.precommit)
        msg = f"Updated repo urls in {CONFIG_PATH.precommit}:"
        for url, new_url in updated_repos:
            msg += f"\n  {url} -> {new_url}"
        raise PrecommitError(msg)
