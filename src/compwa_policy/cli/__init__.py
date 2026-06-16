r"""Typer-based command-line interface for the developer-file checks.

This package gives :program:`check-dev-files` a grouped subcommand structure under a
short top-level :program:`policy` command. You can see which commands are available by
running

.. code-block:: shell

    policy --help

The per-check modules in :mod:`compwa_policy` are unchanged; only the
dispatch and option parsing live here. Running :program:`policy` without a subcommand
runs every check, exactly like the :doc:`/check-dev-files` pre-commit hook.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import rich
import typer
from rich.tree import Tree
from typer.core import TyperGroup

from compwa_policy.cli import env, github, migrate, nb, python, repo
from compwa_policy.cli import format as _format
from compwa_policy.cli._checks import run_all
from compwa_policy.cli._options import (
    DevPythonVersion,
    DocAptPackages,
    NoRuff,
    PackageManager,
    PytestSingleThreaded,
    Python,
    RepoName,
    RepoOrganization,
    RepoTitle,
    build_arguments,
)

if TYPE_CHECKING:
    from typer._click import Command, Context, HelpFormatter


class _HelpGroup(TyperGroup):
    """Append a Rich tree of the command hierarchy to the top-level help."""

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
        super().format_help(ctx, formatter)

        def _add(command: Command, name: str, parent: Tree) -> None:
            first_line = (command.help or "").split("\n")[0]
            label = (
                f"[bold]{name}[/bold]  [dim]{first_line}[/dim]" if first_line else name
            )
            branch = parent.add(label)
            subcommands: dict[str, Command] | None = getattr(command, "commands", None)
            if subcommands:
                for sub_name, sub_command in subcommands.items():
                    _add(sub_command, sub_name, branch)

        rich.print()
        tree = Tree("[bold]policy[/bold]")
        for name, command in self.commands.items():
            _add(command, name, tree)
        rich.print(tree)


app = typer.Typer(
    cls=_HelpGroup,
    help="Standardize and synchronize the developer setup of a ComPWA repository.",
    no_args_is_help=False,
)
app.command("python", no_args_is_help=False)(python.python)
app.command("github", no_args_is_help=False)(github.github)
app.command("env", no_args_is_help=False)(env.env)
app.command("nb", no_args_is_help=False)(nb.nb)
app.command("format", no_args_is_help=False)(_format.format_)
app.command("repo", no_args_is_help=False)(repo.repo)
app.command("migrate", no_args_is_help=False)(migrate.migrate)


@app.callback(invoke_without_command=True)
def run_everything(  # noqa: PLR0917
    ctx: typer.Context,
    python: Python = None,
    dev_python_version: DevPythonVersion = None,
    package_manager: PackageManager = None,
    repo_name: RepoName = None,
    repo_organization: RepoOrganization = None,
    repo_title: RepoTitle = None,
    no_ruff: NoRuff = None,
    pytest_single_threaded: PytestSingleThreaded = None,
    doc_apt_packages: DocAptPackages = None,
) -> None:
    """Run every check at once (this is what the ``check-dev-files`` hook does).

    Only the options shared across the whole repository are accepted here, mirroring
    the top-level ``[tool.compwa.policy]`` table. Options scoped to a single area are
    configured in the matching ``[tool.compwa.policy.<group>]`` sub-table, or passed to
    the corresponding subcommand (e.g. ``policy github --no-pypi``).
    """
    if ctx.invoked_subcommand is not None:
        return
    args = build_arguments(
        python=python,
        dev_python_version=dev_python_version,
        package_manager=package_manager,
        repo_name=repo_name,
        repo_organization=repo_organization,
        repo_title=repo_title,
        no_ruff=no_ruff,
        pytest_single_threaded=pytest_single_threaded,
        doc_apt_packages=doc_apt_packages,
    )
    raise typer.Exit(code=run_all(args))


def get_click_command() -> Command:
    """Return the :program:`policy` app as a Click command.

    This bridges the Typer app to the Click layer so that the ``pwa`` command can mount
    it as a subcommand through a ``pwa.commands`` entry point, without either package
    depending on the other.
    """
    return typer.main.get_command(app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
