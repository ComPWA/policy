# noqa: D100
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import PlainScalarString

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit.getters import find_repo_with_index

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.precommit.struct import Hook, PrecommitConfig, Repo


def remove_precommit_hook(
    precommit: ModifiablePrecommit, hook_id: str, repo_url: str | None = None
) -> None:
    repo_and_hook_idx = __find_repo_and_hook_idx(precommit.document, hook_id, repo_url)
    if repo_and_hook_idx is None:
        return
    repo_idx, hook_idx = repo_and_hook_idx
    repos = precommit.document["repos"]
    hooks = repos[repo_idx]["hooks"]
    if len(hooks) <= 1:
        repos.pop(repo_idx)
    else:
        hooks.pop(hook_idx)
    msg = f"Removed {hook_id!r} hook"
    precommit.changelog.append(msg)


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


def update_single_hook_precommit_repo(
    precommit: ModifiablePrecommit, expected: Repo
) -> None:
    """Update the repo definition in :code:`.pre-commit-config.yaml`.

    If the repository is not yet listed under the :code:`repos` key, a new entry will
    be automatically inserted. If the repository exists, but the definition is not the
    same as expected, the entry in the YAML config will be updated.
    """
    expected_yaml = CommentedMap(expected)
    repos = precommit.document.get("repos", [])
    repo_url = expected["repo"]
    idx_and_repo = find_repo_with_index(precommit.document, repo_url)
    hook_id = expected["hooks"][0]["id"]
    if idx_and_repo is None:
        if not expected_yaml.get("rev"):
            expected_yaml.pop("rev", None)
            expected_yaml.insert(1, "rev", "PLEASE-UPDATE")
        idx = _determine_expected_repo_index(precommit.document, hook_id)
        repos_yaml = cast(CommentedSeq, repos)
        repos_yaml.insert(idx, expected_yaml)
        if isinstance(repos_yaml, CommentedSeq):
            repos_yaml.yaml_set_comment_before_after_key(
                idx if idx + 1 == len(repos) else idx + 1,
                before="\n",
            )
        msg = f"Added {hook_id} hook to {CONFIG_PATH.precommit}."
        precommit.changelog.append(msg)
    if idx_and_repo is None:
        return
    idx, existing_hook = idx_and_repo
    if not _is_equivalent_repo(existing_hook, expected):
        existing_rev = existing_hook.get("rev")
        if existing_rev is not None:
            expected_yaml.insert(1, "rev", PlainScalarString(existing_rev))
        repos[idx] = expected_yaml  # type: ignore[assignment,call-overload]
        repos_map = cast(CommentedMap, repos)
        repos_map.yaml_set_comment_before_after_key(idx + 1, before="\n")
        msg = f"Updated {hook_id} hook"
        precommit.changelog.append(msg)


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


def update_precommit_hook(
    precommit: ModifiablePrecommit, repo_url: str, expected_hook: Hook
) -> None:
    """Update the pre-commit hook definition of a specific pre-commit repo.

    This function updates the :code:`.pre-commit-config.yaml` file, but does this only
    for a specific hook definition *within* a pre-commit repository definition.
    """
    idx_and_repo = find_repo_with_index(precommit.document, repo_url)
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
            repos = cast(CommentedMap, precommit.document["repos"][hook_idx])
            repos.yaml_set_comment_before_after_key(repo_idx + 1, before="\n")
        msg = f"Added {expected_hook['id']!r} to {repo_name} pre-commit config"
        precommit.changelog.append(msg)

    if hooks[hook_idx] != expected_hook:
        hooks[hook_idx] = expected_hook
        msg = f"Updated args of {expected_hook['id']!r} {repo_name} pre-commit hook"
        precommit.changelog.append(msg)


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
