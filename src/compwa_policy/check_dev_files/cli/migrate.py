"""``policy migrate`` — move a repo's ``check-dev-files`` hook args into ``pyproject.toml``.

The flags that used to be repeated under ``args:`` in ``.pre-commit-config.yaml`` can be
declared once in a ``[tool.compwa.policy]`` table instead (see the ``_settings``
module). This command reads the args of the ``check-dev-files`` hook, validates them
against the current parser, writes them into the hierarchical ``[tool.compwa.policy]``
table of ``pyproject.toml``, and removes the now-redundant ``args`` from the hook.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, get_origin

import rich
import rtoml
import typer
from rich.syntax import Syntax

from compwa_policy.check_dev_files import _get_environment_variables
from compwa_policy.check_dev_files.cli._settings import (
    POLICY_TABLE,
    Settings,
    policy_sub_table,
)
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit.struct import Hook

_HOOK_ID = "check-dev-files"

ConfigFileArgument = Annotated[
    Path,
    typer.Argument(help="Path to the .pre-commit-config.yaml file to migrate."),
]
DryRunOption = Annotated[
    bool,
    typer.Option(
        "--dry-run", help="Only report the migration; do not modify any files."
    ),
]

#: Which subcommand group now owns each ``check-dev-files`` flag.
GROUP_FLAGS: dict[str, tuple[str, ...]] = {
    "python": (
        "--allow-vscode-coverage-gutters",
        "--excluded-python-versions",
        "--imports-on-top",
        "--keep-local-precommit",
        "--no-ruff",
        "--pytest-single-threaded",
        "--type-checker",
    ),
    "github": (
        "--allow-deprecated-workflows",
        "--allow-labels",
        "--ci-skipped-tests",
        "--doc-apt-packages",
        "--github-pages",
        "--keep-pr-linting",
        "--keep-workflow",
        "--macos-python-version",
        "--no-cd",
        "--no-github-actions",
        "--no-milestones",
        "--no-pypi",
        "--no-version-branches",
        "--upgrade-frequency",
    ),
    "env": (
        "--environment-variables",
        "--keep-contributing-md",
        "--package-manager",
    ),
    "nb": (
        "--allowed-cell-metadata",
        "--no-binder",
    ),
    "format": ("--no-cspell-update",),
    "repo": (
        "--gitpod",
        "--keep-issue-templates",
    ),
}
#: Flags that are shared by several groups and stay on the run-all hook.
_SHARED_FLAGS = (
    "--dev-python-version",
    "--python",
    "--no-python",
    "--repo-name",
    "--repo-organization",
    "--repo-title",
)
#: Every flag the ``check-dev-files`` hook still accepts.
_KNOWN_FLAGS = {flag for flags in GROUP_FLAGS.values() for flag in flags} | set(
    _SHARED_FLAGS
)


def migrate(
    config_file: ConfigFileArgument = CONFIG_PATH.precommit,
    dry_run: DryRunOption = False,
) -> None:
    """Move the check-dev-files hook args into a pyproject.toml policy table."""
    if not config_file.exists():
        rich.print(f"[red]No such file:[/red] {config_file}")
        raise typer.Exit(code=1)
    if not CONFIG_PATH.pyproject.exists():
        rich.print(f"[red]No such file:[/red] {CONFIG_PATH.pyproject}")
        raise typer.Exit(code=1)
    precommit = ModifiablePrecommit.load(config_file)
    hook = _find_hook(precommit)
    if hook is None:
        rich.print(f"[yellow]No '{_HOOK_ID}' hook found in {config_file}[/yellow]")
        raise typer.Exit(code=0)
    args = list(hook.get("args", []))
    if not args:
        rich.print(f"[green]The '{_HOOK_ID}' hook has no args to migrate.[/green]")
        raise typer.Exit(code=0)
    _validate(args)
    policy = _build_policy(args)
    rich.print("[bold]Adding to pyproject.toml:[/bold]")
    rich.print(Syntax(_render(policy), "toml", background_color="default"))
    if dry_run:
        rich.print("[cyan](dry run: no files changed)[/cyan]")
        raise typer.Exit(code=0)
    _write_pyproject(policy)
    _strip_hook_args(precommit, hook)
    rich.print(
        f"[green]Moved the args of '{_HOOK_ID}' into {CONFIG_PATH.pyproject}.[/green]"
    )


def _find_hook(precommit: ModifiablePrecommit) -> Hook | None:
    for repo in precommit.document.get("repos", []):
        for hook in repo.get("hooks", []):
            if hook.get("id") == _HOOK_ID:
                return hook
    return None


def _validate(args: list[str]) -> None:
    """Ensure every flag is still recognized by the ``check-dev-files`` hook."""
    unknown = sorted({arg.split("=", 1)[0] for arg in args} - _KNOWN_FLAGS)
    if unknown:
        rich.print(
            f"[red]Unrecognized check-dev-files args:[/red] {', '.join(unknown)}"
        )
        raise typer.Exit(code=1)


def _flag_to_field(flag: str) -> str:
    return flag.lstrip("-").replace("-", "_")


def _is_list_field(field_name: str) -> bool:
    return get_origin(Settings.model_fields[field_name].annotation) is list


def _build_policy(args: list[str]) -> dict[str, Any]:
    """Group ``check-dev-files`` args into the nested ``[tool.compwa.policy]`` structure.

    >>> _build_policy(["--no-pypi", "--repo-name=demo", "--type-checker=ty"])
    {'github': {'no-pypi': True}, 'repo-name': 'demo', 'python': {'type-checker': ['ty']}}
    >>> _build_policy(["--no-python", "--environment-variables=A=1,B=2"])
    {'python': False, 'setup': {'env': {'A': '1', 'B': '2'}}}
    """
    policy: dict[str, Any] = {}
    environment_variables: dict[str, str] = {}
    for arg in args:
        flag, separator, raw_value = arg.partition("=")
        if flag in {"--python", "--no-python"}:
            policy["python"] = flag == "--python"
            continue
        field = _flag_to_field(flag)
        if field == "environment_variables":
            environment_variables.update(_get_environment_variables(raw_value))
            continue
        sub_table = policy_sub_table(field)
        target = policy if sub_table is None else policy.setdefault(sub_table, {})
        key = field.replace("_", "-")
        if not separator:
            target[key] = True
        elif _is_list_field(field):
            target.setdefault(key, []).append(raw_value)
        else:
            target[key] = raw_value
    if environment_variables:
        policy.setdefault("setup", {})["env"] = environment_variables
    return policy


def _render(policy: dict[str, Any]) -> str:
    document = {"tool": {"compwa": {"policy": policy}}}
    return rtoml.dumps(document, pretty=True).strip()


def _write_pyproject(policy: dict[str, Any]) -> None:
    pyproject = ModifiablePyproject.load()
    try:
        with pyproject:
            _apply(pyproject, policy)
            pyproject.changelog.append(f"imported args of the '{_HOOK_ID}' hook")
    except PrecommitError:
        pass


def _apply(pyproject: ModifiablePyproject, policy: dict[str, Any]) -> None:
    root = pyproject.get_table(POLICY_TABLE, create=True)
    for key, value in policy.items():
        if not isinstance(value, dict):
            root[key] = value
            continue
        header = f"{POLICY_TABLE}.{key}"
        sub_table = pyproject.get_table(header, create=True)
        for sub_key, sub_value in value.items():
            if isinstance(sub_value, dict):
                nested = pyproject.get_table(f"{header}.{sub_key}", create=True)
                nested.update(sub_value)
            else:
                sub_table[sub_key] = sub_value


def _strip_hook_args(precommit: ModifiablePrecommit, hook: Hook) -> None:
    try:
        with precommit:
            del hook["args"]
            precommit.changelog.append(
                f"moved args of the '{_HOOK_ID}' hook into {CONFIG_PATH.pyproject}"
            )
    except PrecommitError:
        pass
