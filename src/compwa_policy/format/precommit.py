"""Check content of :code:`.pre-commit-config.yaml` and related files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.precommit.getters import find_repo
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap

    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.precommit import ModifiablePrecommit, PrecommitConfig
    from compwa_policy.utilities.session import Session


@check_hook(
    group="format",
    paths=[CONFIG_PATH.precommit, CONFIG_PATH.conda, CONFIG_PATH.pyproject],
)
def check(session: Session, _: Arguments, ctx: CheckContext) -> None:
    precommit = session.precommit
    _sort_hooks(precommit)
    _update_conda_environment(precommit)
    _remove_precommit_ci_section(precommit)
    _update_notebook_hooks(precommit, ctx.has_notebooks)
    _update_repo_urls(precommit)
    if session.pyproject is not None:
        session.pyproject.remove_dependency("pre-commit")
        session.pyproject.remove_dependency("pre-commit-uv")
        session.pyproject.remove_dependency("prek")


def _sort_hooks(precommit: ModifiablePrecommit) -> None:
    repos = precommit.document.get("repos")
    if repos is None:
        return
    sorted_repos = sorted(repos, key=__repo_sort_key)
    if sorted_repos != repos:
        repos[:] = sorted_repos  # in place, to keep the round-trip container
        msg = "Sorted all pre-commit hooks"
        precommit.changelog.append(msg)


def __repo_sort_key(repo: Repo) -> tuple[int, str]:  # ruff: ignore[too-many-return-statements]
    repo_url = repo["repo"]
    if repo_url == "meta":
        return 0, repo_url
    hook_ids = [hook["id"] for hook in repo["hooks"]]
    if "check-dev-files" in hook_ids:
        return 1, repo_url
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


NOTEBOOK_HOOK_IDS = (
    "colab-toc-visible",
    "fix-nbformat-version",
    "remove-empty-tags",
    "set-nb-cells",
    "set-nb-display-name",
    "strip-nb-whitespace",
)
"""Hook IDs that were extracted from ComPWA/policy into ComPWA/nbhooks."""
__NBHOOKS_REPO_URL = "https://github.com/ComPWA/nbhooks"

__DEFAULT_NOTEBOOK_HOOK_IDS = (
    "remove-empty-tags",
    "set-nb-display-name",
    "strip-nb-whitespace",
)


def _update_notebook_hooks(precommit: ModifiablePrecommit, has_notebooks: bool) -> None:
    migrate_notebook_hooks_to_nbhooks(precommit, add_default_hooks=has_notebooks)


def migrate_notebook_hooks_to_nbhooks(
    precommit: ModifiablePrecommit, *, add_default_hooks: bool = False
) -> None:
    """Move notebook hooks from the ComPWA/policy repo entry to ComPWA/nbhooks.

    The notebook hooks used to be served from ComPWA/policy itself, but they now live in
    `ComPWA/nbhooks <https://github.com/ComPWA/nbhooks>`_. Any notebook hook still
    listed under the ComPWA/policy repo is moved to a ComPWA/nbhooks repo entry. When
    :code:`add_default_hooks` is set, the default notebook hooks are added as well (this
    is what the ``check-dev-files`` hook does for repositories that contain notebooks).
    """
    migrated = _pop_policy_notebook_hooks(precommit)
    existing = _get_nbhooks_hooks(precommit)
    hooks_by_id = {**existing, **migrated}
    if add_default_hooks:
        for hook_id in __DEFAULT_NOTEBOOK_HOOK_IDS:
            hooks_by_id.setdefault(hook_id, Hook(id=hook_id))
    if not hooks_by_id:
        return
    hooks = [hooks_by_id[hook_id] for hook_id in sorted(hooks_by_id)]
    # An empty rev makes update_single_hook_precommit_repo pin the latest tag when the
    # repo entry is created and keep the existing rev when it already exists.
    precommit.update_single_hook_repo(
        Repo(repo=__NBHOOKS_REPO_URL, rev="", hooks=hooks)
    )


def _pop_policy_notebook_hooks(precommit: ModifiablePrecommit) -> dict[str, Hook]:
    """Remove notebook hooks from the ComPWA/policy repo and return them by ID."""
    policy_repo = precommit.find_repo(r".*/(ComPWA\-)?policy")
    if policy_repo is None:
        return {}
    migrated = {
        hook["id"]: hook
        for hook in policy_repo["hooks"]
        if hook["id"] in NOTEBOOK_HOOK_IDS
    }
    for hook_id in migrated:
        precommit.remove_hook(hook_id, repo_url=policy_repo["repo"])
    return migrated


def _get_nbhooks_hooks(precommit: ModifiablePrecommit) -> dict[str, Hook]:
    nbhooks_repo = precommit.find_repo(r".*/nbhooks")
    if nbhooks_repo is None:
        return {}
    return {hook["id"]: hook for hook in nbhooks_repo["hooks"]}


def _remove_precommit_ci_section(precommit: ModifiablePrecommit) -> None:
    """Remove the :code:`ci` section that configures pre-commit.ci.

    ComPWA repositories run their hooks through `ComPWA/actions
    <https://github.com/ComPWA/actions>`_ instead of through `pre-commit.ci
    <https://pre-commit.ci>`_, so the section no longer has any effect.
    """
    if "ci" not in precommit.document:
        return
    del precommit.document["ci"]
    msg = "Removed pre-commit.ci configuration"
    precommit.changelog.append(msg)


def _update_conda_environment(precommit: ModifiablePrecommit) -> None:
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
            precommit.changelog.append(f"Set {key} environment variable in {path}")
    elif key in variables:
        del variables[key]
        if not variables:
            del conda_env["variables"]
        yaml.dump(conda_env, path)
        precommit.changelog.append(f"Removed {key} environment variable {path}")


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
