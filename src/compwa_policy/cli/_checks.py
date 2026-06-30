"""Canonical check dispatch shared by the run-all hook and the :program:`policy` subcommands.

:func:`run_checks` lists every check exactly once, in the order the original
``check-dev-files`` hook ran them, with each line guarded by the subcommand *group* it
belongs to. :func:`run_all` runs every group; a subcommand runs only its own. The
individual checks themselves live under the `compwa_policy` modules and are unchanged.
"""

from __future__ import annotations

from typing import Literal, get_args

import typer
from attrs import frozen

from compwa_policy import Arguments, _get_environment_variables, _to_list
from compwa_policy._characterization import has_python_code
from compwa_policy.env import conda, direnv, pixi, uv
from compwa_policy.errors import PolicyError
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
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    use_modifiable_pyproject,
)


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
    try:
        with (
            ModifiablePrecommit.load() as precommit_config,
            use_modifiable_pyproject() as (pyproject_config, _),
        ):
            changes = run_checks(
                precommit_config,
                pyproject_config,
                args,
                ctx,
                groups=groups,
            )
            changes += precommit_config.changelog
            if pyproject_config is not None:
                changes += pyproject_config.changelog
    except PolicyError as exception:
        print("\n".join(exception.args))  # noqa: T201
        return 1
    if changes:
        print("\n--------------------\n".join(changes))  # noqa: T201
        return 1
    return 0


def run_checks(  # noqa: C901, PLR0912, PLR0915
    precommit_config: ModifiablePrecommit,
    pyproject_config: ModifiablePyproject | None,
    args: Arguments,
    ctx: Context,
    *,
    groups: frozenset[Group] = ALL_GROUPS,
) -> list[str]:
    """Dispatch the requested check *groups* in the canonical order.

    This is the single source of truth for which checks run and in what order. Running
    with every group (the default) reproduces the original flat ``check-dev-files``
    dispatch exactly; a subcommand passes only its own group. Keeping one ordered
    sequence means a subcommand can never order a shared config file (such as
    ``.pre-commit-config.yaml``) differently from the full run.
    """
    changes: list[str] = []
    if "repo" in groups:
        changes += citation.main(precommit_config)
        changes += commitlint.main()
    if "env" in groups:
        changes += conda.main(args.dev_python_version, args.package_manager)
    if "github" in groups:
        changes += dependabot.main(args.upgrade_frequency)
    if "format" in groups:
        editorconfig.main(precommit_config)
    if "github" in groups and not args.allow_labels:
        changes += labels.main()
    if "github" in groups and not args.no_github_actions:
        changes += workflows.main(
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
            changes += binder.main(
                args.package_manager,
                args.dev_python_version,
                ctx.doc_apt_packages,
            )
        changes += jupyter.main(args.no_ruff, pyproject_config)
    if "nb" in groups:
        nbstripout.main(
            precommit_config,
            ctx.has_notebooks,
            _to_list(args.allowed_cell_metadata),
        )
    if "env" in groups:
        changes += pixi.main(
            args.package_manager,
            ctx.is_python_repo,
            args.dev_python_version,
            pyproject_config,
        )
        changes += direnv.main(args.package_manager, ctx.environment_variables)
    if "format" in groups:
        changes += toml.main(  # has to run before pre-commit
            precommit_config,
            pyproject_config,
        )
    if "repo" in groups:
        changes += poe.main(ctx.has_notebooks, args.package_manager, pyproject_config)
    if "format" in groups:
        changes += prettier.main(precommit_config)
    if "python" in groups and ctx.is_python_repo and args.no_ruff:
        changes += black.main(precommit_config, ctx.has_notebooks, pyproject_config)
    if "github" in groups and ctx.is_python_repo and not args.no_github_actions:
        changes += release_drafter.main(
            args.no_cd,
            args.repo_name,
            args.repo_title,
            args.repo_organization,
        )
    if "python" in groups and ctx.is_python_repo:
        changes += pyproject.main(args.excluded_python_versions, pyproject_config)
        changes += mypy.main(
            "mypy" in args.type_checker,
            precommit_config,
            pyproject_config,
        )
        changes += pyright.main(
            "pyright" in args.type_checker,
            precommit_config,
            pyproject_config,
        )
        changes += ty.main(args.type_checker, precommit_config, pyproject_config)
        changes += pytest.main(
            args.allow_vscode_coverage_gutters,
            args.pytest_single_threaded,
            args.branch_coverage,
            pyproject_config,
        )
        changes += pyupgrade.main(precommit_config, args.no_ruff)
        if not args.no_ruff:
            changes += ruff.main(
                precommit_config,
                ctx.has_notebooks,
                args.imports_on_top,
                pyproject_config,
            )
    if "github" in groups and args.upgrade_frequency != "no":
        changes += upgrade_lock.main(
            precommit_config,
            frequency=args.upgrade_frequency,
            keep_workflow=args.keep_workflow,
        )
    if "repo" in groups:
        changes += readthedocs.main(args.package_manager, args.dev_python_version)
        changes += remove_deprecated_tools(precommit_config, args.keep_issue_templates)
        changes += vscode.main(
            ctx.has_notebooks,
            ctx.is_python_repo,
            args.package_manager,
        )
        changes += gitpod.main(args.gitpod, args.dev_python_version)
    if "format" in groups:
        precommit.main(precommit_config, ctx.has_notebooks, pyproject_config)
    if "env" in groups:
        changes += uv.main(
            precommit_config,
            args.dev_python_version,
            args.keep_contributing_md,
            args.package_manager,
            args.repo_organization,
            args.repo_name,
            pyproject_config,
        )
    if "format" in groups:
        changes += cspell.main(precommit_config, args.no_cspell_update)
    return changes
