"""``policy migrate`` — rewrite a repo's ``check-dev-files`` hook args into the new structure.

The flag interface itself is unchanged, but the flags are now *owned* by a subcommand
group (see :mod:`compwa_policy.check_dev_files.cli`). This command validates the args of
the ``check-dev-files`` hook in a ``.pre-commit-config.yaml`` against the current parser,
reports which group each flag now belongs to, and rewrites the ``args`` list into a
canonical, sorted form.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import rich
import typer

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit import ModifiablePrecommit

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
        "--dry-run", help="Only report the migration; do not modify the file."
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


def _flag_group(flag: str) -> str:
    for group, flags in GROUP_FLAGS.items():
        if flag in flags:
            return group
    if flag in _SHARED_FLAGS:
        return "shared"
    return "unknown"


def migrate(
    config_file: ConfigFileArgument = CONFIG_PATH.precommit,
    dry_run: DryRunOption = False,
) -> None:
    """Rewrite the check-dev-files hook args into the new grouped structure."""
    if not config_file.exists():
        rich.print(f"[red]No such file:[/red] {config_file}")
        raise typer.Exit(code=1)
    precommit = ModifiablePrecommit.load(config_file)
    hook = _find_hook(precommit)
    if hook is None:
        rich.print(f"[yellow]No '{_HOOK_ID}' hook found in {config_file}[/yellow]")
        raise typer.Exit(code=0)
    old_args = list(hook.get("args", []))
    _validate(old_args)
    _report(old_args)
    new_args = _normalize(old_args)
    if new_args == old_args:
        rich.print("[green]Already up to date.[/green]")
        raise typer.Exit(code=0)
    if dry_run:
        rich.print("[cyan]Would rewrite args to:[/cyan]")
        for arg in new_args:
            rich.print(f"  {arg}")
        raise typer.Exit(code=0)
    with precommit:
        hook["args"] = new_args
        precommit.changelog.append(
            f"sorted and validated args of the '{_HOOK_ID}' hook"
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


def _report(args: list[str]) -> None:
    grouped: dict[str, list[str]] = {}
    for arg in args:
        flag = arg.split("=", 1)[0]
        grouped.setdefault(_flag_group(flag), []).append(arg)
    rich.print("[bold]Flags by subcommand group:[/bold]")
    for group in sorted(grouped):
        rich.print(f"  [bold]{group}[/bold]: {', '.join(sorted(grouped[group]))}")


def _normalize(args: list[str]) -> list[str]:
    """Return the args sorted by their flag name (``append`` order is preserved).

    >>> _normalize(["--no-pypi", "--allow-labels", "--keep-workflow=a"])
    ['--allow-labels', '--keep-workflow=a', '--no-pypi']
    """
    return sorted(args, key=lambda arg: arg.split("=", 1)[0])
