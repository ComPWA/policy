"""``policy migrate`` — upgrade a repository's :file:`.pre-commit-config.yaml`.

The flags that used to be repeated under ``args:`` in ``.pre-commit-config.yaml`` can be
declared once in a ``[tool.compwa.policy]`` table instead (see the ``_settings``
module). This command reads the args of the ``check-dev-files`` hook, validates them
against the current parser, writes them into the hierarchical ``[tool.compwa.policy]``
table of ``pyproject.toml``, and removes the now-redundant ``args`` from the hook.

It also relocates any notebook formatting hooks that are still served from the
ComPWA/policy repo entry to a `ComPWA/nbhooks <https://github.com/ComPWA/nbhooks>`_ repo
entry, since those hooks were extracted into a separate repository.
"""

from __future__ import annotations

import contextlib
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, get_origin

import rich
import rtoml
import typer
from rich.syntax import Syntax

from compwa_policy import _get_environment_variables
from compwa_policy.cli._settings import POLICY_TABLE, Settings, policy_sub_table
from compwa_policy.errors import PrecommitError
from compwa_policy.format.precommit import (
    __NBHOOKS_REPO_URL,
    NOTEBOOK_HOOK_IDS,
    migrate_notebook_hooks_to_nbhooks,
)
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
        "--branch-coverage",
        "--excluded-python-versions",
        "--imports-on-top",
        "--no-branch-coverage",
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
    """Migrate hook args into a pyproject.toml policy table and relocate nb hooks."""
    _assert_inputs_exist(config_file)
    precommit = ModifiablePrecommit.load(config_file)
    hook = _find_hook(precommit)
    if hook is None:
        rich.print(f"[yellow]No '{_HOOK_ID}' hook found in {config_file}[/yellow]")
        raise typer.Exit(code=0)
    args = list(hook.get("args", []))
    notebook_hooks = _find_relocatable_notebook_hooks(precommit)
    if not args and not notebook_hooks:
        rich.print(f"[green]The '{_HOOK_ID}' hook has nothing to migrate.[/green]")
        raise typer.Exit(code=0)

    policy = _build_validated_policy(args)
    _report_plan(policy, notebook_hooks)
    if dry_run:
        rich.print("[cyan](dry run: no files changed)[/cyan]")
        raise typer.Exit(code=0)

    if policy:
        _write_pyproject(policy)
    _apply_precommit_changes(
        precommit, hook, strip_args=bool(args), relocate=bool(notebook_hooks)
    )
    _report_result(has_args=bool(args), notebook_hooks=notebook_hooks)


def _assert_inputs_exist(config_file: Path) -> None:
    if not config_file.exists():
        rich.print(f"[red]No such file:[/red] {config_file}")
        raise typer.Exit(code=1)


def _build_validated_policy(args: list[str]) -> dict[str, Any]:
    if not args:
        return {}
    _validate(args)
    return _build_policy(args)


def _report_plan(policy: dict[str, Any], notebook_hooks: list[str]) -> None:
    if policy:
        rich.print("[bold]Adding to pyproject.toml:[/bold]")
        rich.print(Syntax(_render(policy), "toml", background_color="default"))
    if notebook_hooks:
        rich.print(
            f"[bold]Moving notebook hooks to {__NBHOOKS_REPO_URL}:[/bold]"
            f" {', '.join(notebook_hooks)}"
        )


def _report_result(*, has_args: bool, notebook_hooks: list[str]) -> None:
    if has_args:
        rich.print(
            f"[green]Moved the args of '{_HOOK_ID}' into {CONFIG_PATH.pyproject}.[/green]"
        )
    if notebook_hooks:
        rich.print(f"[green]Moved notebook hooks to {__NBHOOKS_REPO_URL}.[/green]")


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
        raw_value = _unquote_cli_value(raw_value)
        if flag in {"--python", "--no-python"}:
            policy["python"] = flag == "--python"
            continue
        if flag in {"--branch-coverage", "--no-branch-coverage"}:
            sub_table = policy_sub_table("branch_coverage")
            target = policy if sub_table is None else policy.setdefault(sub_table, {})
            target["branch-coverage"] = flag == "--branch-coverage"
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


def _unquote_cli_value(value: str) -> str:
    """Strip shell quotes from a single option value carried through YAML.

    In a shell, ``--repo-title="ComPWA demos"`` arrives as ``--repo-title=ComPWA
    demos``. In a pre-commit YAML ``args`` list, the quote characters are part of the
    scalar, so migration has to remove them explicitly.
    """
    try:
        values = shlex.split(value)
    except ValueError:
        return value
    if len(values) == 1:
        return values[0]
    return value


def _render(policy: dict[str, Any]) -> str:
    document = {"tool": {"compwa": {"policy": policy}}}
    return rtoml.dumps(document, pretty=True).strip()


def _write_pyproject(policy: dict[str, Any]) -> None:
    pyproject = ModifiablePyproject.load(
        CONFIG_PATH.pyproject if CONFIG_PATH.pyproject.exists() else ""
    )
    try:
        with pyproject:
            _apply(pyproject, policy)
            if not CONFIG_PATH.pyproject.exists():
                pyproject.dump(CONFIG_PATH.pyproject)
            pyproject.changelog.append(f"imported args of the '{_HOOK_ID}' hook")
    except PrecommitError:
        pass


def _apply(pyproject: ModifiablePyproject, policy: dict[str, Any]) -> None:
    _apply_table(pyproject, POLICY_TABLE, policy)


def _apply_table(
    pyproject: ModifiablePyproject, header: str, table: dict[str, Any]
) -> None:
    """Write ``table`` under ``header``, creating a section only when it has keys.

    A table is materialized only if it holds scalar keys of its own; parents that
    contain nothing but sub-tables are left for :func:`create_sub_table` to emit as
    super-tables, so no empty ``[header]`` sections are written.
    """
    scalars = {
        key: value for key, value in table.items() if not isinstance(value, dict)
    }
    if scalars:
        pyproject.get_table(header, create=True).update(scalars)
    for key, value in table.items():
        if isinstance(value, dict):
            _apply_table(pyproject, f"{header}.{key}", value)


def _find_relocatable_notebook_hooks(precommit: ModifiablePrecommit) -> list[str]:
    """List the notebook hook IDs still served from the ComPWA/policy repo entry."""
    policy_repo = precommit.find_repo(r".*/(ComPWA\-)?policy")
    if policy_repo is None:
        return []
    return [
        hook["id"] for hook in policy_repo["hooks"] if hook["id"] in NOTEBOOK_HOOK_IDS
    ]


def _apply_precommit_changes(
    precommit: ModifiablePrecommit, hook: Hook, *, strip_args: bool, relocate: bool
) -> None:
    with contextlib.suppress(PrecommitError), precommit:
        if strip_args:
            del hook["args"]
            precommit.changelog.append(
                f"moved args of the '{_HOOK_ID}' hook into {CONFIG_PATH.pyproject}"
            )
        if relocate:
            migrate_notebook_hooks_to_nbhooks(precommit)
