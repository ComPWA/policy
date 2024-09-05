"""Check content of :code:`.pre-commit-config.yaml` and related files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ruamel.yaml.comments import CommentedMap

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit.getters import find_repo
from compwa_policy.utilities.precommit.struct import Hook
from compwa_policy.utilities.python import has_constraint_files
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import (
        ModifiablePrecommit,
        Precommit,
        PrecommitConfig,
        Repo,
    )


def main(precommit: ModifiablePrecommit, has_notebooks: bool) -> None:
    with Executor() as do:
        do(_sort_hooks, precommit)
        do(_update_conda_environment, precommit)
        do(_update_precommit_ci_commit_msg, precommit)
        do(_update_precommit_ci_skip, precommit)
        do(_update_policy_hook, precommit, has_notebooks)
        do(_update_repo_urls, precommit)


def _sort_hooks(precommit: ModifiablePrecommit) -> None:
    repos = precommit.document.get("repos")
    if repos is None:
        return
    sorted_repos = sorted(repos, key=__repo_sort_key)
    if sorted_repos != repos:
        precommit.document["repos"] = sorted_repos
        msg = "Sorted all pre-commit hooks"
        precommit.append_to_changelog(msg)


def __repo_sort_key(repo: Repo) -> tuple[int, str]:
    repo_url = repo["repo"]
    if repo_url == "meta":
        return 0, repo_url
    if re.match(r"^.*/(ComPWA-)?policy$", repo_url) is not None:
        return 1, repo_url
    hooks = repo["hooks"]
    if any(hook["id"] == "nbstripout" for hook in hooks):
        return 2, repo_url
    if len(hooks) > 1:
        return 3, repo_url
    hook_id = hooks[0]["id"]
    formatter_hooks = {
        "black",
        "blacken-docs",
        "isort",
        "prettier",
        "taplo",
        "taplo-format",
        "toml-sort",
    }
    if hook_id in formatter_hooks:
        return 4, hook_id
    return 5, hook_id


def _update_policy_hook(precommit: ModifiablePrecommit, has_notebooks: bool) -> None:
    if not has_notebooks:
        return
    repo = precommit.find_repo(r".*/(ComPWA\-)?policy")
    if repo is None:
        msg = "Could not find ComPWA/policy pre-commit repo"
        raise KeyError(msg)
    hook_ids = {h["id"] for h in repo["hooks"]}
    remove_empty_tags_ids = "remove-empty-tags"
    if remove_empty_tags_ids in hook_ids:
        return
    precommit.update_hook(
        repo_url=repo["repo"],
        expected_hook=Hook(id=remove_empty_tags_ids),
    )


def _update_precommit_ci_commit_msg(precommit: ModifiablePrecommit) -> None:
    precommit_ci = precommit.document.get("ci")
    if precommit_ci is None:
        return
    if has_constraint_files():
        expected_msg = "MAINT: update pip constraints and pre-commit"
    else:
        expected_msg = "MAINT: autoupdate pre-commit hooks"
    key = "autoupdate_commit_msg"
    autoupdate_commit_msg = precommit_ci.get(key)
    if autoupdate_commit_msg != expected_msg:
        precommit_ci[key] = expected_msg  # type:ignore[literal-required]
        msg = f"Set ci.{key} to {expected_msg!r}"
        precommit.append_to_changelog(msg)


def _update_precommit_ci_skip(precommit: ModifiablePrecommit) -> None:
    precommit_ci = precommit.document.get("ci")
    if precommit_ci is None:
        return
    local_hooks = get_local_hooks(precommit.document)
    non_functional_hooks = get_non_functional_hooks(precommit.document)
    expected_skips = sorted(set(non_functional_hooks) | set(local_hooks))
    existing_skips = precommit_ci.get("skip")
    if not expected_skips and existing_skips is not None:
        del precommit_ci["skip"]
        msg = "Removed redundant ci.skip section"
        precommit.append_to_changelog(msg)
    if existing_skips != expected_skips:
        precommit_ci["skip"] = sorted(expected_skips)
        yaml_config = cast(CommentedMap, precommit.document)
        yaml_config.yaml_set_comment_before_after_key("repos", before="\n")
        msg = "Updated ci.skip section"
        precommit.append_to_changelog(msg)


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


def _update_conda_environment(precommit: Precommit) -> None:
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
    if __has_prettier_v4alpha(precommit.document):
        if key not in variables:
            variables[key] = 1
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


def _update_repo_urls(precommit: ModifiablePrecommit) -> None:
    redirects = {
        r"^.*github\.com/ComPWA/repo-maintenance$": "https://github.com/ComPWA/policy",
    }
    repos = precommit.document["repos"]
    updated_repos: list[tuple[str, str]] = []
    for repo in repos:
        url = repo["repo"]
        for redirect, new_url in redirects.items():
            if re.match(redirect, url):
                repo["repo"] = new_url
                updated_repos.append((url, new_url))
    if updated_repos:
        msg = "Updated repo URLs:"
        for url, new_url in updated_repos:
            msg += f"\n  {url} -> {new_url}"
        precommit.append_to_changelog(msg)
