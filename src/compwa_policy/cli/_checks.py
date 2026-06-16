"""Canonical check dispatch shared by the run-all hook and the :program:`policy` subcommands.

:func:`run_checks` lists every check exactly once, in the order the original
``check-dev-files`` hook ran them, with each line guarded by the subcommand *group* it
belongs to. :func:`run_all` runs every group; a subcommand runs only its own. The
individual checks themselves live in the ``compwa_policy.*`` modules and
are unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, get_args

import typer
from attrs import frozen

from compwa_policy import Arguments, _get_environment_variables, _to_list
from compwa_policy._characterization import has_python_code
from compwa_policy.env import conda, direnv, pixi, uv
from compwa_policy.format import cspell, editorconfig, precommit, prettier, toml
from compwa_policy.github import (
    dependabot,
    labels,
    release_drafter,
    upgrade_lock,
    workflows,
)
from compwa_policy.nb import binder, jupyter, nbstripout
from compwa_policy.python import (
    black,
    mypy,
    pyproject,
    pyright,
    pytest,
    pyupgrade,
    ruff,
    ty,
)
from compwa_policy.repo import citation, commitlint, gitpod, poe, readthedocs, vscode
from compwa_policy.repo.deprecated import remove_deprecated_tools
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import Pyproject

if TYPE_CHECKING:
    from compwa_policy.utilities.executor import Executor as _Executor


@frozen
class Context:
    """Repository properties that are derived once and shared by every check."""

    is_python_repo: bool
    has_notebooks: bool
    doc_apt_packages: list[str]
    environment_variables: dict[str, str]


def compute_context(args: Arguments) -> Context:
    return Context(
        is_python_repo=has_python_code() if args.python is None else args.python,
        has_notebooks=is_committed("**/*.ipynb"),
        doc_apt_packages=_to_list(args.doc_apt_packages),
        environment_variables=_get_environment_variables(args.environment_variables),
    )


def check_dev_python_version(args: Arguments) -> int:
    """Return ``1`` if the requested dev Python version is not supported."""
    if CONFIG_PATH.pyproject.exists():
        supported_versions = Pyproject.load().get_supported_python_versions()
        if supported_versions and args.dev_python_version not in supported_versions:
            print(  # noqa: T201
                f"The specified development Python version {args.dev_python_version} is"
                " not listed in the supported Python versions of pyproject.toml:"
                f" {', '.join(sorted(supported_versions))}"
            )
            return 1
    return 0


Group = Literal["python", "github", "env", "nb", "format", "repo"]
ALL_GROUPS: frozenset[Group] = frozenset(get_args(Group))


def run_all(args: Arguments) -> int:
    """Run every check at once, as the ``check-dev-files`` hook does."""
    return _run(args, ALL_GROUPS)


def dispatch(args: Arguments, group: Group) -> None:
    """Run a single subcommand group and translate its exit code into a Typer exit."""
    raise typer.Exit(code=_run(args, frozenset({group})))


def _run(args: Arguments, groups: frozenset[Group]) -> int:
    if check_dev_python_version(args):
        return 1
    ctx = compute_context(args)
    with (
        Executor(raise_exception=False) as do,
        ModifiablePrecommit.load() as precommit_config,
    ):
        run_checks(do, precommit_config, args, ctx, groups=groups)
    return 1 if do.error_messages else 0


def run_checks(  # noqa: C901, PLR0912, PLR0915
    do: _Executor,
    precommit_config: ModifiablePrecommit,
    args: Arguments,
    ctx: Context,
    *,
    groups: frozenset[Group] = ALL_GROUPS,
) -> None:
    """Dispatch the requested check *groups* in the canonical order.

    This is the single source of truth for which checks run and in what order. Running
    with every group (the default) reproduces the original flat ``check-dev-files``
    dispatch exactly; a subcommand passes only its own group. Keeping one ordered
    sequence means a subcommand can never order a shared config file (such as
    ``.pre-commit-config.yaml``) differently from the full run.
    """
    if "repo" in groups:
        do(citation.main, precommit_config)
        do(commitlint.main)
    if "env" in groups:
        do(conda.main, args.dev_python_version, args.package_manager)
    if "github" in groups:
        do(dependabot.main, args.upgrade_frequency)
    if "format" in groups:
        do(editorconfig.main, precommit_config)
    if "github" in groups and not args.allow_labels:
        do(labels.main)
    if "github" in groups and not args.no_github_actions:
        do(
            workflows.main,
            precommit_config,
            allow_deprecated=args.allow_deprecated_workflows,
            doc_apt_packages=ctx.doc_apt_packages,
            environment_variables=ctx.environment_variables,
            github_pages=args.github_pages,
            keep_pr_linting=args.keep_pr_linting,
            macos_python_version=args.macos_python_version,
            no_cd=args.no_cd,
            no_milestones=args.no_milestones,
            no_pypi=args.no_pypi,
            no_version_branches=args.no_version_branches,
            python_version=args.dev_python_version,
            single_threaded=args.pytest_single_threaded,
            skip_tests=_to_list(args.ci_skipped_tests),
        )
    if "nb" in groups and ctx.has_notebooks:
        if not args.no_binder:
            do(
                binder.main,
                args.package_manager,
                args.dev_python_version,
                ctx.doc_apt_packages,
            )
        do(jupyter.main, args.no_ruff)
    if "nb" in groups:
        do(
            nbstripout.main,
            precommit_config,
            ctx.has_notebooks,
            _to_list(args.allowed_cell_metadata),
        )
    if "env" in groups:
        do(pixi.main, args.package_manager, ctx.is_python_repo, args.dev_python_version)
        do(direnv.main, args.package_manager, ctx.environment_variables)
    if "format" in groups:
        do(toml.main, precommit_config)  # has to run before pre-commit
    if "repo" in groups:
        do(poe.main, ctx.has_notebooks, args.package_manager)
    if "format" in groups:
        do(prettier.main, precommit_config)
    if "python" in groups and ctx.is_python_repo and args.no_ruff:
        do(black.main, precommit_config, ctx.has_notebooks)
    if "github" in groups and ctx.is_python_repo and not args.no_github_actions:
        do(
            release_drafter.main,
            args.no_cd,
            args.repo_name,
            args.repo_title,
            args.repo_organization,
        )
    if "python" in groups and ctx.is_python_repo:
        do(pyproject.main, args.excluded_python_versions)
        do(mypy.main, "mypy" in args.type_checker, precommit_config)
        do(pyright.main, "pyright" in args.type_checker, precommit_config)
        do(ty.main, args.type_checker, args.keep_local_precommit, precommit_config)
        do(pytest.main, args.allow_vscode_coverage_gutters, args.pytest_single_threaded)
        do(pyupgrade.main, precommit_config, args.no_ruff)
        if not args.no_ruff:
            do(ruff.main, precommit_config, ctx.has_notebooks, args.imports_on_top)
    if "github" in groups and args.upgrade_frequency != "no":
        do(
            upgrade_lock.main,
            precommit_config,
            frequency=args.upgrade_frequency,
            keep_workflow=args.keep_workflow,
        )
    if "repo" in groups:
        do(readthedocs.main, args.package_manager, args.dev_python_version)
        do(remove_deprecated_tools, precommit_config, args.keep_issue_templates)
        do(vscode.main, ctx.has_notebooks, ctx.is_python_repo, args.package_manager)
        do(gitpod.main, args.gitpod, args.dev_python_version)
    if "format" in groups:
        do(precommit.main, precommit_config, ctx.has_notebooks)
    if "env" in groups:
        do(
            uv.main,
            precommit_config,
            args.dev_python_version,
            args.keep_contributing_md,
            args.package_manager,
            args.repo_organization,
            args.repo_name,
        )
    if "format" in groups:
        do(cspell.main, precommit_config, args.no_cspell_update)
