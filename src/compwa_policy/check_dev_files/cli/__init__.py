r"""Typer-based command-line interface for the developer-file checks.

This package gives :program:`check-dev-files` a grouped subcommand structure under a
short top-level :program:`policy` command. You can see which commands are available by
running

.. code-block:: shell

    policy --help

The per-check modules in :mod:`compwa_policy.check_dev_files` are unchanged; only the
dispatch and option parsing live here. Running :program:`policy` without a subcommand
runs every check, exactly like the :doc:`/check-dev-files` pre-commit hook.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import rich
import typer
from rich.tree import Tree
from typer.core import TyperGroup

from compwa_policy.check_dev_files.cli import env, github, migrate, nb, python, repo
from compwa_policy.check_dev_files.cli import format as _format
from compwa_policy.check_dev_files.cli._checks import run_all
from compwa_policy.check_dev_files.cli._options import (
    AllowDeprecatedWorkflows,
    AllowedCellMetadata,
    AllowLabels,
    AllowVscodeCoverageGutters,
    CiSkippedTests,
    DevPythonVersion,
    DocAptPackages,
    EnvironmentVariables,
    ExcludedPythonVersions,
    GithubPages,
    Gitpod,
    ImportsOnTop,
    KeepContributingMd,
    KeepIssueTemplates,
    KeepLocalPrecommit,
    KeepPrLinting,
    KeepWorkflow,
    MacosPythonVersion,
    NoBinder,
    NoCd,
    NoCspellUpdate,
    NoGithubActions,
    NoMilestones,
    NoPypi,
    NoRuff,
    NoVersionBranches,
    PackageManager,
    PytestSingleThreaded,
    Python,
    RepoName,
    RepoOrganization,
    RepoTitle,
    TypeCheckerOption,
    UpgradeFrequency,
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
    environment_variables: EnvironmentVariables = None,
    excluded_python_versions: ExcludedPythonVersions = None,
    no_ruff: NoRuff = None,
    imports_on_top: ImportsOnTop = None,
    type_checker: TypeCheckerOption = None,
    keep_local_precommit: KeepLocalPrecommit = None,
    pytest_single_threaded: PytestSingleThreaded = None,
    allow_vscode_coverage_gutters: AllowVscodeCoverageGutters = None,
    allow_labels: AllowLabels = None,
    allow_deprecated_workflows: AllowDeprecatedWorkflows = None,
    no_github_actions: NoGithubActions = None,
    github_pages: GithubPages = None,
    keep_pr_linting: KeepPrLinting = None,
    macos_python_version: MacosPythonVersion = None,
    no_cd: NoCd = None,
    no_milestones: NoMilestones = None,
    no_pypi: NoPypi = None,
    no_version_branches: NoVersionBranches = None,
    ci_skipped_tests: CiSkippedTests = None,
    doc_apt_packages: DocAptPackages = None,
    keep_workflow: KeepWorkflow = None,
    upgrade_frequency: UpgradeFrequency = None,
    no_binder: NoBinder = None,
    allowed_cell_metadata: AllowedCellMetadata = None,
    no_cspell_update: NoCspellUpdate = None,
    gitpod: Gitpod = None,
    keep_contributing_md: KeepContributingMd = None,
    keep_issue_templates: KeepIssueTemplates = None,
) -> None:
    """Run every check at once (this is what the ``check-dev-files`` hook does)."""
    if ctx.invoked_subcommand is not None:
        return
    args = build_arguments(
        python=python,
        dev_python_version=dev_python_version,
        package_manager=package_manager,
        repo_name=repo_name,
        repo_organization=repo_organization,
        repo_title=repo_title,
        environment_variables=environment_variables,
        excluded_python_versions=excluded_python_versions,
        no_ruff=no_ruff,
        imports_on_top=imports_on_top,
        type_checker=type_checker,
        keep_local_precommit=keep_local_precommit,
        pytest_single_threaded=pytest_single_threaded,
        allow_vscode_coverage_gutters=allow_vscode_coverage_gutters,
        allow_labels=allow_labels,
        allow_deprecated_workflows=allow_deprecated_workflows,
        no_github_actions=no_github_actions,
        github_pages=github_pages,
        keep_pr_linting=keep_pr_linting,
        macos_python_version=macos_python_version,
        no_cd=no_cd,
        no_milestones=no_milestones,
        no_pypi=no_pypi,
        no_version_branches=no_version_branches,
        ci_skipped_tests=ci_skipped_tests,
        doc_apt_packages=doc_apt_packages,
        keep_workflow=keep_workflow,
        upgrade_frequency=upgrade_frequency,
        no_binder=no_binder,
        allowed_cell_metadata=allowed_cell_metadata,
        no_cspell_update=no_cspell_update,
        gitpod=gitpod,
        keep_contributing_md=keep_contributing_md,
        keep_issue_templates=keep_issue_templates,
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
