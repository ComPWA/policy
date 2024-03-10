"""Helper functions for modifying :file:`.pre-commit.config.yaml`."""

from __future__ import annotations

import re
import socket
import sys
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from pre_commit.commands.autoupdate import autoupdate as precommit_autoupdate
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import PlainScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if sys.version_info < (3, 8):
    from typing_extensions import Literal, TypedDict
else:
    from typing import Literal, TypedDict
if sys.version_info < (3, 11):
    from typing_extensions import NotRequired
else:
    from typing import NotRequired
if TYPE_CHECKING:
    from pathlib import Path

    from ruamel.yaml import YAML


def load_precommit_config(path: Path = CONFIG_PATH.precommit) -> PrecommitConfig:
    """Load a **read-only** pre-commit config."""
    config, _ = load_roundtrip_precommit_config(path)
    return config


def load_roundtrip_precommit_config(
    path: Path = CONFIG_PATH.precommit,
) -> tuple[PrecommitConfig, YAML]:
    """Load the pre-commit config as a round-trip YAML object."""
    yaml_parser = create_prettier_round_trip_yaml()
    config = yaml_parser.load(path)
    return config, yaml_parser


def find_repo(config: PrecommitConfig, search_pattern: str) -> Repo | None:
    """Find pre-commit repo definition in pre-commit config."""
    repos = config.get("repos", [])
    for repo in repos:
        url = repo.get("repo", "")
        if re.search(search_pattern, url):
            return repo
    return None


def find_repo_with_index(
    config: PrecommitConfig, search_pattern: str
) -> tuple[int, Repo] | None:
    """Find pre-commit repo definition and its index in pre-commit config."""
    repos = config.get("repos", [])
    for i, repo in enumerate(repos):
        url = repo.get("repo", "")
        if re.search(search_pattern, url):
            return i, repo
    return None


def remove_precommit_hook(hook_id: str, repo_url: str | None = None) -> None:
    config, yaml = load_roundtrip_precommit_config()
    repo_and_hook_idx = __find_repo_and_hook_idx(config, hook_id, repo_url)
    if repo_and_hook_idx is None:
        return
    repo_idx, hook_idx = repo_and_hook_idx
    repos = config["repos"]
    hooks = repos[repo_idx]["hooks"]
    if len(hooks) <= 1:
        repos.pop(repo_idx)
    else:
        hooks.pop(hook_idx)
    yaml.dump(config, CONFIG_PATH.precommit)
    msg = f"Removed {hook_id!r} from {CONFIG_PATH.precommit}"
    raise PrecommitError(msg)


def __find_repo_and_hook_idx(
    config: PrecommitConfig, hook_id: str, repo_url: str | None = None
) -> tuple[int, int] | None:
    repos = config.get("repos", [])
    for repo_idx, repo in enumerate(repos):
        if repo_url is not None and repo.get("repo") != repo_url:
            continue
        hooks = repo.get("hooks", [])
        for hook_idx, hook in enumerate(hooks):
            if hook.get("id") == hook_id:
                return repo_idx, hook_idx
    return None


def update_single_hook_precommit_repo(expected: Repo) -> None:
    """Update the repo definition in :code:`.pre-commit-config.yaml`.

    If the repository is not yet listed under the :code:`repos` key, a new entry will
    be automatically inserted. If the repository exists, but the definition is not the
    same as expected, the entry in the YAML config will be updated.
    """
    if not CONFIG_PATH.precommit.exists():
        return
    expected_yaml = CommentedMap(expected)
    config, yaml = load_roundtrip_precommit_config()
    repos = config.get("repos", [])
    repo_url = expected["repo"]
    idx_and_repo = find_repo_with_index(config, repo_url)
    hook_id = expected["hooks"][0]["id"]
    if idx_and_repo is None:
        if not expected_yaml.get("rev"):
            expected_yaml.pop("rev", None)
            expected_yaml.insert(1, "rev", "PLEASE-UPDATE")
        idx = _determine_expected_repo_index(config, hook_id)
        repos_yaml = cast(CommentedSeq, repos)
        repos_yaml.insert(idx, expected_yaml)
        repos_yaml.yaml_set_comment_before_after_key(
            idx if idx + 1 == len(repos) else idx + 1,
            before="\n",
        )
        yaml.dump(config, CONFIG_PATH.precommit)
        if has_internet_connection():
            precommit_autoupdate(
                CONFIG_PATH.precommit,
                freeze=False,
                repos=[repo_url],
                tags_only=True,
            )
        msg = f"Added {hook_id} hook to {CONFIG_PATH.precommit}."
        raise PrecommitError(msg)
    idx, existing_hook = idx_and_repo
    if not _is_equivalent_repo(existing_hook, expected):
        existing_rev = existing_hook.get("rev")
        if existing_rev is not None:
            expected_yaml.insert(1, "rev", PlainScalarString(existing_rev))
        repos[idx] = expected_yaml  # type: ignore[assignment,call-overload]
        repos_map = cast(CommentedMap, repos)
        repos_map.yaml_set_comment_before_after_key(idx + 1, before="\n")
        yaml.dump(config, CONFIG_PATH.precommit)
        msg = f"Updated {hook_id} hook in {CONFIG_PATH.precommit}"
        raise PrecommitError(msg)


def _determine_expected_repo_index(config: PrecommitConfig, hook_id: str) -> int:
    repos = config["repos"]
    for i, repo_def in enumerate(repos):
        hooks = repo_def["hooks"]
        if len(hooks) != 1:
            continue
        if hook_id.lower() <= repo_def["hooks"][0]["id"].lower():
            return i
    return len(repos)


def _is_equivalent_repo(expected: Repo, existing: Repo) -> bool:
    def remove_rev(repo: Repo) -> dict:
        repo_copy = dict(repo)
        repo_copy.pop("rev", None)
        return repo_copy

    return remove_rev(expected) == remove_rev(existing)


def update_precommit_hook(repo_url: str, expected_hook: Hook) -> None:
    """Update the pre-commit hook definition of a specific pre-commit repo.

    This function updates the :code:`.pre-commit-config.yaml` file, but does this only
    for a specific hook definition *within* a pre-commit repository definition.
    """
    if not CONFIG_PATH.precommit.exists():
        return
    config, yaml = load_roundtrip_precommit_config()
    idx_and_repo = find_repo_with_index(config, repo_url)
    if idx_and_repo is None:
        return
    repo_idx, repo = idx_and_repo
    repo_name = repo_url.split("/")[-1]
    hooks = repo["hooks"]
    hook_idx = __find_hook_idx(hooks, expected_hook["id"])
    if hook_idx is None:
        hook_idx = __determine_expected_hook_idx(hooks, expected_hook["id"])
        hooks.insert(hook_idx, expected_hook)
        if hook_idx == len(hooks) - 1:
            repos = cast(CommentedMap, config["repos"])
            repos.yaml_set_comment_before_after_key(repo_idx + 1, before="\n")
        yaml.dump(config, CONFIG_PATH.precommit)
        msg = f"Added {expected_hook['id']!r} to {repo_name} pre-commit config"
        raise PrecommitError(msg)

    if hooks[hook_idx] != expected_hook:
        hooks[hook_idx] = expected_hook
        yaml.dump(config, CONFIG_PATH.precommit)
        msg = f"Updated args of {expected_hook['id']!r} {repo_name} pre-commit hook"
        raise PrecommitError(msg)


def __find_hook_idx(hooks: list[Hook], hook_id: str) -> int | None:
    msg = ""
    for i, hook in enumerate(hooks):
        msg += " " + hook["id"]
        if hook["id"] == hook_id:
            return i
    return None


def __determine_expected_hook_idx(hooks: list[Hook], hook_id: str) -> int:
    for i, hook in enumerate(hooks):
        if hook["id"] > hook_id:
            return i
    return len(hooks)


@lru_cache(maxsize=None)
def has_internet_connection(
    host: str = "8.8.8.8", port: int = 53, timeout: float = 0.5
) -> bool:
    try:
        # cspell:ignore setdefaulttimeout
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
    except OSError:
        return False
    else:
        return True


class PrecommitConfig(TypedDict):
    """https://pre-commit.com/#pre-commit-configyaml---top-level."""

    ci: NotRequired[PrecommitCi]
    repos: list[Repo]
    default_stages: NotRequired[list[str]]
    files: NotRequired[str]
    exclude: NotRequired[str]
    fail_fast: NotRequired[bool]
    minimum_pre_commit_version: NotRequired[str]


class PrecommitCi(TypedDict):
    """https://pre-commit.ci/#configuration."""

    autofix_commit_msg: NotRequired[str]
    autofix_prs: NotRequired[bool]
    autoupdate_branch: NotRequired[str]
    autoupdate_commit_msg: NotRequired[str]
    autoupdate_schedule: NotRequired[Literal["weekly", "monthly", "quarterly"]]
    skip: NotRequired[list[str]]
    submodules: NotRequired[bool]


class Repo(TypedDict):
    """https://pre-commit.com/#pre-commit-configyaml---repos."""

    repo: str
    rev: str
    hooks: list[Hook]


class Hook(TypedDict):
    """https://pre-commit.com/#pre-commit-configyaml---hooks."""

    id: str
    alias: NotRequired[str]
    name: NotRequired[str]
    language_version: NotRequired[str]
    files: NotRequired[str]
    exclude: NotRequired[str]
    types: NotRequired[list[str]]
    types_or: NotRequired[list[str]]
    exclude_types: NotRequired[list[str]]
    args: NotRequired[list[str]]
    stages: NotRequired[list[str]]
    additional_dependencies: NotRequired[list[str]]
    always_run: NotRequired[bool]
    verbose: NotRequired[bool]
    log_file: NotRequired[str]
    pass_filenames: NotRequired[bool]
