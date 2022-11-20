"""Checks to be performed locally on the ComPWA/repo-maintenance repository."""
from functools import lru_cache
from io import StringIO
from textwrap import dedent, indent
from typing import Dict

import yaml

from repoma.errors import PrecommitError
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import Hook, PrecommitConfig

__HOOK_DEFINITION_FILE = ".pre-commit-hooks.yaml"
__IGNORE_KEYS = {"args"}


def main() -> int:
    cfg = PrecommitConfig.load()
    local_repos = [repo for repo in cfg.repos if repo.repo == "local"]
    executor = Executor()
    for repo in local_repos:
        for hook in repo.hooks:
            executor(_check_hook_definition, hook)
    if executor.error_messages:
        print(executor.merge_messages())
        return 1
    return 0


def _check_hook_definition(hook: Hook) -> None:
    hook_definitions = _load_precommit_hook_definitions()
    expected = hook_definitions.get(hook.id)
    if expected is None:
        return
    if _to_dict(hook) != _to_dict(expected):
        msg = f"""
        Local hook with ID '{hook.id}' does not match the definitions in
        {__HOOK_DEFINITION_FILE}. Should be at least:
        """
        msg = dedent(msg).replace("\n", " ")
        stream = StringIO()
        yaml.dump([_to_dict(expected)], stream, sort_keys=False)
        expected_content = indent(stream.getvalue(), prefix="  ")
        raise PrecommitError(msg + "\n\n" + expected_content)


def _to_dict(hook: Hook) -> dict:
    hook_dict = hook.dict(skip_defaults=True)
    return {k: v for k, v in hook_dict.items() if k not in __IGNORE_KEYS}


@lru_cache(maxsize=None)
def _load_precommit_hook_definitions() -> Dict[str, Hook]:
    with open(__HOOK_DEFINITION_FILE) as f:
        hook_definitions = yaml.load(f, Loader=yaml.SafeLoader)
    hooks = [Hook(**h) for h in hook_definitions]
    hook_ids = [h.id for h in hooks]
    if len(hook_ids) != len(set(hook_ids)):
        raise PrecommitError(f"{__HOOK_DEFINITION_FILE} contains duplicate IDs")
    return {h.id: h for h in hooks}


if __name__ == "__main__":
    raise SystemExit(main())
