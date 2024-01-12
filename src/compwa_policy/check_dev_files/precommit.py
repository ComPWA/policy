"""Check content of :code:`.pre-commit-config.yaml` and related files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import (
    PrecommitConfig,
    find_repo,
    load_round_trip_precommit_config,
)
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml


def main() -> None:
    executor = Executor()
    executor(_sort_hooks)
    executor(_update_conda_environment)
    executor(_update_precommit_ci_commit_msg)
    executor(_update_precommit_ci_skip)
    executor.finalize()


def _sort_hooks() -> None:
    yaml = create_prettier_round_trip_yaml()
    contents: CommentedMap = yaml.load(CONFIG_PATH.precommit)
    repos: CommentedSeq | None = contents.get("repos")
    if repos is None:
        return
    sorted_repos: list[CommentedMap] = sorted(repos, key=__repo_def_sorting)
    contents["repos"] = sorted_repos
    if sorted_repos != repos:
        yaml.dump(contents, CONFIG_PATH.precommit)
        msg = f"Sorted pre-commit hooks in {CONFIG_PATH.precommit}"
        raise PrecommitError(msg)


def __repo_def_sorting(repo_def: CommentedMap) -> tuple[int, str]:
    if repo_def["repo"] == "meta":
        return (0, "meta")
    hooks: CommentedSeq = repo_def["hooks"]
    if len(hooks) > 1:
        return 1, repo_def["repo"]
    return (2, hooks[0]["id"])


def _update_precommit_ci_commit_msg() -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    config, yaml = load_round_trip_precommit_config()
    precommit_ci = config.get("ci")
    if precommit_ci is None:
        return
    if CONFIG_PATH.pip_constraints.exists():
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


def _update_precommit_ci_skip() -> None:
    config, _ = load_round_trip_precommit_config()
    if config.get("ci") is None:
        return
    local_hooks = get_local_hooks(config)
    non_functional_hooks = get_non_functional_hooks(config)
    expected_skips = set(non_functional_hooks) | set(local_hooks)
    if not expected_skips:
        if config.get("ci", {}).get("skip") is not None:
            yaml = create_prettier_round_trip_yaml()
            contents: CommentedMap = yaml.load(CONFIG_PATH.precommit)
            del contents.get("ci")["skip"]
            contents.yaml_set_comment_before_after_key("repos", before="\n")
            yaml.dump(contents, CONFIG_PATH.precommit)
            msg = f"No need for a ci.skip in {CONFIG_PATH.precommit}"
            raise PrecommitError(msg)
        return
    existing_skips = __get_precommit_ci_skips(config)
    if existing_skips != expected_skips:
        __update_precommit_ci_skip(expected_skips)


def __update_precommit_ci_skip(expected_skips: Iterable[str]) -> None:
    yaml = create_prettier_round_trip_yaml()
    contents = yaml.load(CONFIG_PATH.precommit)
    ci_section: CommentedMap = contents.get("ci")
    if "skip" in ci_section.ca.items:
        del ci_section.ca.items["skip"]
    skips = CommentedSeq(sorted(expected_skips))
    ci_section["skip"] = skips
    contents.yaml_set_comment_before_after_key("repos", before="\n")
    yaml.dump(contents, CONFIG_PATH.precommit)
    msg = f"Updated ci.skip section in {CONFIG_PATH.precommit}"
    raise PrecommitError(msg)


def __get_precommit_ci_skips(config: PrecommitConfig) -> set[str]:
    precommit_ci = config.get("ci")
    if precommit_ci is None:
        msg = "Pre-commit config does not contain a ci section"
        raise ValueError(msg)
    return set(precommit_ci.get("skip", []))


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
    precommit_config, _ = load_round_trip_precommit_config()
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
    idx_and_repo = find_repo(config, search_pattern=r"^.*/mirrors-prettier$")
    if idx_and_repo is None:
        return False
    _, repo = idx_and_repo
    rev = repo.get("rev", "")
    return rev.startswith("v4") and "alpha" in rev
