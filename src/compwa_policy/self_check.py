"""Checks to be performed locally on the ComPWA/policy repository itself."""

from __future__ import annotations

from io import StringIO
from textwrap import dedent, indent

import yaml

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.executor import executor
from compwa_policy.utilities.precommit import Hook, load_precommit_config

__HOOK_DEFINITION_FILE = ".pre-commit-hooks.yaml"


def main() -> int:
    cfg = load_precommit_config()
    local_repos = [repo for repo in cfg["repos"] if repo["repo"] == "local"]
    hook_definitions = _load_precommit_hook_definitions()
    with executor(raise_exception=False) as do:
        for repo in local_repos:
            for hook in repo["hooks"]:
                do(_check_hook_definition, hook, hook_definitions)
    return 1 if do.error_messages else 0


def _load_precommit_hook_definitions() -> dict[str, Hook]:
    with open(__HOOK_DEFINITION_FILE) as f:
        hooks: list[Hook] = yaml.load(f, Loader=yaml.SafeLoader)
    hook_ids = [h["id"] for h in hooks]
    if len(hook_ids) != len(set(hook_ids)):
        msg = f"{__HOOK_DEFINITION_FILE} contains duplicate IDs"
        raise PrecommitError(msg)
    return {h["id"]: h for h in hooks}


def _check_hook_definition(hook: Hook, definitions: dict[str, Hook]) -> None:
    expected = definitions.get(hook["id"])
    if expected is None:
        return
    if __reduce(hook) != __reduce(expected):
        msg = f"""
        Local hook with ID '{hook["id"]}' does not match the definitions in
        {__HOOK_DEFINITION_FILE}. Should be at least:
        """
        msg = dedent(msg).replace("\n", " ")
        stream = StringIO()
        yaml.dump([__reduce(expected)], stream, sort_keys=False)
        expected_content = indent(stream.getvalue(), prefix="  ")
        raise PrecommitError(msg + "\n\n" + expected_content)


def __reduce(hook: Hook) -> dict:
    ignore_keys = {"args"}
    return {k: v for k, v in hook.items() if k not in ignore_keys}


if __name__ == "__main__":
    raise SystemExit(main())
