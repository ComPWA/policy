"""Check content of :code:`.pre-commit-config.yaml` and related files."""

from textwrap import dedent
from typing import List, Set

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import PrecommitConfig
from repoma.utilities.yaml import create_prettier_round_trip_yaml

__NON_SKIPPED_HOOKS = {
    "editorconfig-checker",
}
__SKIPPED_HOOKS = {
    "check-jsonschema",
    "pyright",
    "taplo",
}


def main() -> None:
    cfg = PrecommitConfig.load()
    executor = Executor()
    executor(_check_plural_hooks_first, cfg)
    executor(_check_single_hook_sorting, cfg)
    executor(_check_skipped_hooks, cfg)
    executor.finalize()


def _check_plural_hooks_first(config: PrecommitConfig) -> None:
    if config.ci is None:
        return
    plural_hook_repos = [r for r in config.repos if len(r.hooks) > 1]
    n_plural_repos = len(plural_hook_repos)
    if config.repos[:n_plural_repos] != plural_hook_repos:
        msg = (
            "Please bundle repos with multiple hooks at the top of the pre-commit"
            " config"
        )
        raise PrecommitError(msg)


def _check_single_hook_sorting(config: PrecommitConfig) -> None:
    if config.ci is None:
        return
    single_hook_repos = [r for r in config.repos if len(r.hooks) == 1]
    expected_repo_order = sorted(
        (r for r in single_hook_repos),
        key=lambda r: r.hooks[0].id,
    )
    if single_hook_repos != expected_repo_order:
        msg = "Pre-commit hooks are not sorted. Should be as follows:\n\n  "
        msg += "\n  ".join(f"{r.hooks[0].id:20s} {r.repo}" for r in expected_repo_order)
        raise PrecommitError(msg)


def _check_skipped_hooks(config: PrecommitConfig) -> None:
    if config.ci is None:
        return
    local_hooks = get_local_hooks(config)
    non_functional_hooks = get_non_functional_hooks(config)
    expected_skips = set(non_functional_hooks) | set(local_hooks)
    if not expected_skips:
        if config.ci.skip is not None:
            yaml = create_prettier_round_trip_yaml()
            contents: CommentedMap = yaml.load(CONFIG_PATH.precommit)
            del contents["ci"]["skip"]
            contents.yaml_set_comment_before_after_key("repos", before="\n")
            yaml.dump(contents, CONFIG_PATH.precommit)
            msg = f"No need for a ci.skip in {CONFIG_PATH.precommit}"
            raise PrecommitError(msg)
        return
    existing_skips = __get_precommit_ci_skips(config)
    if existing_skips != expected_skips:
        yaml = create_prettier_round_trip_yaml()
        contents = yaml.load(CONFIG_PATH.precommit)
        ci_section: CommentedMap = contents["ci"]
        if "skip" in ci_section.ca.items:
            del ci_section.ca.items["skip"]
        skips = CommentedSeq(sorted(expected_skips))
        ci_section["skip"] = skips
        contents.yaml_set_comment_before_after_key("repos", before="\n")
        yaml.dump(contents, CONFIG_PATH.precommit)
        msg = f"Updated ci.skip section in {CONFIG_PATH.precommit}"
        raise PrecommitError(msg)
    hooks_to_execute = __NON_SKIPPED_HOOKS & existing_skips
    if hooks_to_execute:
        msg = f"""
        Please remove the following hooks from the ci.skip section of {CONFIG_PATH.precommit}:

            {', '.join(sorted(hooks_to_execute))}
        """
        msg = dedent(msg)
        raise PrecommitError(msg)


def __get_precommit_ci_skips(config: PrecommitConfig) -> Set[str]:
    if config.ci is None:
        msg = "Pre-commit config does not contain a ci section"
        raise ValueError(msg)
    if config.ci.skip is None:
        return set()
    return set(config.ci.skip)


def get_local_hooks(config: PrecommitConfig) -> List[str]:
    return [h.id for r in config.repos for h in r.hooks if r.repo == "local"]


def get_non_functional_hooks(config: PrecommitConfig) -> List[str]:
    return [
        hook.id
        for repo in config.repos
        for hook in repo.hooks
        if repo.repo
        if hook.id in __SKIPPED_HOOKS
    ]
