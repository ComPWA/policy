"""Check content of :code:`.pre-commit-config.yaml` and related files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, MutableMapping, cast

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit.getters import find_repo
from compwa_policy.utilities.precommit.struct import Hook
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.python import (
    has_constraint_files,
    split_dependency_definition,
)
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import (
        ModifiablePrecommit,
        Precommit,
        PrecommitConfig,
        Repo,
    )


def main(precommit: ModifiablePrecommit, has_notebooks: bool) -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_sort_hooks, precommit)
        do(_update_conda_environment, precommit)
        do(_update_precommit_ci_commit_msg, precommit)
        do(_update_precommit_ci_skip, precommit)
        do(_update_policy_hook, precommit, has_notebooks)
        do(_update_repo_urls, precommit)
        do(_switch_to_precommit_uv, pyproject)


def _sort_hooks(precommit: ModifiablePrecommit) -> None:
    repos = precommit.document.get("repos")
    if repos is None:
        return
    sorted_repos = sorted(repos, key=__repo_sort_key)
    if sorted_repos != repos:
        precommit.document["repos"] = sorted_repos
        msg = "Sorted all pre-commit hooks"
        precommit.changelog.append(msg)


def __repo_sort_key(repo: Repo) -> tuple[int, str]:  # noqa: PLR0911
    repo_url = repo["repo"]
    if repo_url == "meta":
        return 0, repo_url
    if re.match(r"^.*/(ComPWA-)?policy$", repo_url) is not None:
        return 1, repo_url
    hook_ids = [hook["id"] for hook in repo["hooks"]]
    if any(i == "nbstripout" for i in hook_ids):
        return 2, repo_url
    if any(i == "nbqa-isort" for i in hook_ids):
        return 3, repo_url
    if len(hook_ids) > 1:
        return 4, repo_url
    hook_id = hook_ids[0]
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
        return 5, hook_id
    return 6, hook_id


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
        precommit.changelog.append(msg)


def _update_precommit_ci_skip(precommit: ModifiablePrecommit) -> None:
    precommit_ci = precommit.document.get("ci")
    if precommit_ci is None:
        return
    local_hooks = get_local_hooks(precommit.document)
    non_functional_hooks = get_non_functional_hooks(precommit.document)
    expected_skips = sorted(set(non_functional_hooks) | set(local_hooks))
    existing_skips = precommit_ci.get("skip")
    if existing_skips and existing_skips != expected_skips:
        precommit_ci["skip"] = sorted(expected_skips)
        yaml_config = cast(CommentedMap, precommit.document)
        yaml_config.yaml_set_comment_before_after_key("repos", before="\n")
        msg = "Updated ci.skip section"
        precommit.changelog.append(msg)
    if not expected_skips and existing_skips:
        del precommit_ci["skip"]
        msg = "Removed redundant ci.skip section"
        precommit.changelog.append(msg)


def get_local_hooks(config: PrecommitConfig) -> list[str]:
    repos = config["repos"]
    return [h["id"] for r in repos for h in r["hooks"] if r["repo"] == "local"]


def get_non_functional_hooks(config: PrecommitConfig) -> list[str]:
    skipped_hooks = {
        "check-jsonschema",
        "pyright",
        "taplo",
    }
    return [
        hook["id"]
        for repo in config["repos"]
        for hook in repo["hooks"]
        if repo["repo"]
        if hook["id"] in skipped_hooks
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


def __has_prettier_v4alpha(config: PrecommitConfig) -> bool:
    repo = find_repo(config, search_pattern=r"^.*/(mirrors-)?prettier(-pre-commit)?$")
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
        precommit.changelog.append(msg)


def _switch_to_precommit_uv(pyproject: ModifiablePyproject) -> None:
    __replace_precommit_in_conda()
    __replace_precommit_in_pyproject(pyproject)


def __replace_precommit_in_conda() -> None:
    if not CONFIG_PATH.conda.exists():
        return
    yaml = create_prettier_round_trip_yaml()
    conda_env: CommentedMap = yaml.load(CONFIG_PATH.conda)
    dependencies: CommentedSeq = conda_env.get("dependencies")
    if dependencies is None:
        return
    precommit_idx = ___get_precommit_idx(dependencies)
    if precommit_idx is None:
        return
    dependencies.pop(precommit_idx)
    if "pip" not in dependencies:
        dependencies.append("pip")
    pip_dependencies = ___find_conda_pip_dict(dependencies)
    if pip_dependencies is None:
        pip_dependencies = CommentedMap({"pip": ["pre-commit-uv"]})
        dependencies.append(pip_dependencies)
    else:
        pip_dependencies["pip"].append("pre-commit-uv")
    pip_dependencies["pip"] = sorted(pip_dependencies["pip"])
    yaml.dump(conda_env, CONFIG_PATH.conda)
    msg = f"Switched to pre-commit-uv in {CONFIG_PATH.conda}"
    raise PrecommitError(msg)


def ___get_precommit_idx(dependencies: list[str]) -> int | None:
    for idx, dep in enumerate(dependencies):
        if not isinstance(dep, str):
            continue
        name, *_ = split_dependency_definition(dep)
        if name.lower() == "pre-commit":
            return idx
    return None


def ___find_conda_pip_dict(
    dependencies: CommentedSeq,
) -> CommentedMap | None:
    for dep in dependencies:
        if isinstance(dep, CommentedMap) and "pip" in dep:
            return dep
    return None


def __replace_precommit_in_pyproject(pyproject: ModifiablePyproject) -> None:
    table_key = "project.optional-dependencies"
    if not pyproject.has_table(table_key):
        return
    optional_dependencies = pyproject.get_table(table_key)
    updated = ___update_dependency_group(optional_dependencies, key="dev")
    updated |= ___update_dependency_group(optional_dependencies, key="sty")
    if updated:
        msg = "Switched to pre-commit-uv in pyproject.toml"
        pyproject.changelog.append(msg)


def ___update_dependency_group(
    optional_dependencies: MutableMapping[str, Any], key: str
) -> bool:
    dependencies: list[str] | None = optional_dependencies.get(key)
    if dependencies is None:
        return False
    precommit_idx = ___get_precommit_idx(dependencies)
    if precommit_idx is None:
        return False
    dependencies[precommit_idx] = "pre-commit-uv"
    return True
