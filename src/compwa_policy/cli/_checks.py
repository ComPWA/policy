"""Canonical check dispatch shared by the run-all hook and the :program:`policy` subcommands.

:data:`CHECK_HOOKS` lists every check exactly once, in the order the original
``check-dev-files`` hook ran them. Each definition carries its subcommand group and the
file metadata declared by its check module. :func:`run_all` runs every group; a
subcommand runs only its own. The union of the same definitions produces the pre-commit
file filter.
"""

from __future__ import annotations

from typing import get_args

import typer

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
from compwa_policy.repo import (
    citation,
    commitlint,
    deprecated,
    gitpod,
    poe,
    readthedocs,
    vscode,
)
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import CheckContext, FileSet, Group
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.pyproject import Pyproject
from compwa_policy.utilities.session import Session


def compute_context(args: Arguments) -> CheckContext:
    return CheckContext(
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


ALL_GROUPS: frozenset[Group] = frozenset(get_args(Group))
CHECK_HOOKS = (
    citation.check,
    commitlint.check,
    conda.check,
    editorconfig.check,
    labels.check,
    workflows.check,
    binder.check,
    jupyter.check,
    nbstripout.check,
    pixi.check,
    direnv.check,
    toml.check,
    poe.check,
    prettier.check,
    black.check,
    release_drafter.check,
    pyproject.check,
    mypy.check,
    pyright.check,
    ty.check,
    pytest.check,
    pyupgrade.check,
    ruff.check,
    upgrade_lock.check,
    dependabot.check,
    readthedocs.check,
    deprecated.check,
    vscode.check,
    gitpod.check,
    precommit.check,
    uv.check,
    cspell.check,
)
CHECK_DEV_FILES_PATTERN = FileSet.union(
    tuple(hook.files for hook in CHECK_HOOKS)
).to_regex()


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
        with Session.load() as session:
            run_checks(session, args, ctx, groups=groups)
            changes = session.flush()
    except PolicyError as exception:
        print("\n".join(exception.args))  # noqa: T201
        return 1
    if changes:
        print("\n--------------------\n".join(changes))  # noqa: T201
        return 1
    return 0


def run_checks(
    session: Session,
    args: Arguments,
    ctx: CheckContext,
    *,
    groups: frozenset[Group] = ALL_GROUPS,
) -> None:
    """Dispatch the requested check *groups* in the canonical order.

    :data:`CHECK_HOOKS` is the single source of truth for which checks run and in what
    order. Running with every group (the default) reproduces the original flat
    ``check-dev-files`` dispatch exactly; a subcommand passes only its own group.
    Keeping one ordered sequence means a subcommand can never order a shared config
    file (such as ``.pre-commit-config.yaml``) differently from the full run.

    Each check reports its modifications through the *session*: either by mutating a
    managed container (:attr:`~.Session.pyproject`, :attr:`~.Session.precommit`) or by
    appending to :attr:`~.Session.changelog`. Nothing is returned.
    """
    for hook in CHECK_HOOKS:
        if hook.group in groups:
            hook(session, args, ctx)
