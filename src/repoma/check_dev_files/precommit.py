"""Check content of :code:`.pre-commit-config.yaml` and related files."""
from io import StringIO
from textwrap import dedent, indent
from typing import Iterable, List, Set

import yaml

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.precommit import PrecommitConfig

__NON_SKIPPED_HOOKS = {
    "editorconfig-checker",
}
__SKIPPED_HOOKS = {
    "pyright",
}


def main() -> None:
    cfg = PrecommitConfig.load()
    _check_plural_hooks_first(cfg)
    _check_single_hook_sorting(cfg)
    _check_local_hooks(cfg)
    _check_skipped_hooks(cfg)


def _check_plural_hooks_first(config: PrecommitConfig) -> None:
    if config.ci is None:
        return
    plural_hook_repos = [r for r in config.repos if len(r.hooks) > 1]
    n_plural_repos = len(plural_hook_repos)
    if config.repos[:n_plural_repos] != plural_hook_repos:
        raise PrecommitError(
            "Please bundle repos with multiple hooks at the top of the pre-commit"
            " config"
        )


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


def _check_local_hooks(config: PrecommitConfig) -> None:
    if config.ci is None:
        return
    local_hook_ids = get_local_hooks(config)
    if len(local_hook_ids) == 0:
        return
    skipped_hooks = __get_precommit_ci_skips(config)
    missing_hooks = set(local_hook_ids) - skipped_hooks
    if missing_hooks:
        msg = f"""
        The ci section in {CONFIG_PATH.precommit} should skip local hooks. These local
        hooks are missing: {', '.join(sorted(missing_hooks))}.
        Please add at least the following entries to {CONFIG_PATH.precommit}:
        """
        msg = dedent(msg).replace("\n", " ")
        expected_content = __dump_expected_skips(local_hook_ids)
        raise PrecommitError(msg + "\n\n" + expected_content)


def _check_skipped_hooks(config: PrecommitConfig) -> None:
    if config.ci is None:
        return
    non_functional_hooks = get_non_functional_hooks(config)
    skipped_hooks = __get_precommit_ci_skips(config)
    missing_hooks = set(non_functional_hooks) - skipped_hooks
    if missing_hooks:
        msg = f"""
        The ci section in {CONFIG_PATH.precommit} should skip a few hooks that don't
        work on pre-commit.ci. The following hooks are not listed:
        {', '.join(sorted(missing_hooks))}. Please add at least the following entries
        to {CONFIG_PATH.precommit}:
        """
        msg = dedent(msg)
        expected_content = __dump_expected_skips(non_functional_hooks)
        raise PrecommitError(msg + "\n\n" + expected_content)
    hooks_to_execute = __NON_SKIPPED_HOOKS & skipped_hooks
    if hooks_to_execute:
        msg = f"""
        Please remove the following hooks from the ci.skip section of {CONFIG_PATH.precommit}:

            {', '.join(sorted(hooks_to_execute))}
        """
        msg = dedent(msg)
        raise PrecommitError(msg)


def __dump_expected_skips(hooks: Iterable[str]) -> str:
    stream = StringIO()
    yaml.dump({"ci": {"skip": sorted(hooks)}}, stream, sort_keys=False)
    return indent(stream.getvalue(), prefix="  ")


def __get_precommit_ci_skips(config: PrecommitConfig) -> Set[str]:
    if config.ci is None:
        raise ValueError("Pre-commit config does not contain a ci section")
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
