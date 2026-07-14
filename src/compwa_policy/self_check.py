"""Checks to be performed locally on the ComPWA/policy repository itself."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from ruamel.yaml import YAML

from compwa_policy.cli._checks import CHECK_DEV_FILES_PATTERN
from compwa_policy.errors import PolicyError
from compwa_policy.utilities.precommit import Precommit

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit.struct import Hook

__HOOK_DEFINITION_FILE = ".pre-commit-hooks.yaml"
__PRECOMMIT_FIXTURE_FILE = Path("tests/utilities/precommit/.pre-commit-config.yaml")


def main(precommit: Precommit | None = None) -> int:
    if precommit is None:
        precommit = Precommit.load()
    hook_definitions, manifest = _load_precommit_hook_definitions()
    errors = _get_manifest_errors(hook_definitions)
    if _update_manifest_definition(hook_definitions):
        _write_hook_manifest(manifest)
    precommit_configs = [precommit]
    if __PRECOMMIT_FIXTURE_FILE.exists():
        precommit_configs.append(Precommit.load(__PRECOMMIT_FIXTURE_FILE))
    for config in precommit_configs:
        hooks_updated = [
            _check_hook_definition(hook, hook_definitions)
            for repo in config.document["repos"]
            for hook in repo["hooks"]
        ]
        if any(hooks_updated):
            _write_precommit_config(config)
    if errors:
        print("\n--------------------\n".join(error.strip() for error in errors))  # noqa: T201
        return 1
    return 0


def _load_precommit_hook_definitions() -> tuple[dict[str, Hook], list[Hook]]:
    parser = _create_hook_manifest_parser()
    with open(__HOOK_DEFINITION_FILE) as f:
        hooks: list[Hook] = parser.load(f)
    hook_ids = [h["id"] for h in hooks]
    if len(hook_ids) != len(set(hook_ids)):
        msg = f"{__HOOK_DEFINITION_FILE} contains duplicate IDs"
        raise PolicyError(msg)
    return {h["id"]: h for h in hooks}, hooks


def _get_manifest_errors(definitions: dict[str, Hook]) -> list[str]:
    hook = definitions.get("check-dev-files")
    if hook is None:
        return ["The hook manifest does not define the 'check-dev-files' hook."]
    return []


def _update_manifest_definition(definitions: dict[str, Hook]) -> bool:
    hook = definitions.get("check-dev-files")
    if hook is None or hook.get("files") == CHECK_DEV_FILES_PATTERN:
        return False
    hook["files"] = CHECK_DEV_FILES_PATTERN
    return True


def _write_hook_manifest(hooks: list[Hook]) -> None:
    parser = _create_hook_manifest_parser()
    with open(__HOOK_DEFINITION_FILE, "w") as stream:
        parser.dump(hooks, stream)


def _create_hook_manifest_parser() -> YAML:
    parser = YAML(typ="rt")
    parser.preserve_quotes = True
    return parser


def _check_hook_definition(hook: Hook, definitions: dict[str, Hook]) -> bool:
    expected = definitions.get(hook["id"])
    if expected is None:
        return False
    expected_values = __reduce(expected)
    hook_values = cast("dict[str, object]", hook)
    args_are_last = "args" not in hook_values or next(reversed(hook_values)) == "args"
    if __reduce(hook) == expected_values and args_are_last:
        return False
    args = hook_values.pop("args", None)
    for key in set(hook_values) - set(expected_values) - {"args"}:
        del hook_values[key]
    hook_values.update(expected_values)
    if args is not None:
        hook_values["args"] = args
    return True


def _write_precommit_config(precommit: Precommit) -> None:
    source = precommit.source
    if source is None:
        return
    content = precommit.dumps()
    if isinstance(source, Path):
        source.write_text(content)
        return
    position = source.tell()
    source.seek(0)
    source.write(content)
    source.truncate()
    source.seek(position)


def __reduce(hook: Hook) -> dict[str, object]:
    ignore_keys = {"args"}
    return {k: v for k, v in hook.items() if k not in ignore_keys}


if __name__ == "__main__":
    raise SystemExit(main())
