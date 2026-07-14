"""Bundled developer configurations and tools for ComPWA repositories.

This package provides the :code:`check-dev-files` `pre-commit <https://pre-commit.com>`_
hook (and the :program:`policy` CLI) that standardize and synchronize the developer
setup across the `ComPWA repositories <https://github.com/ComPWA>`_.

The command-line interface lives in :mod:`compwa_policy.cli`. This module only defines
the shared `Arguments` data model and a few string helpers; the `Arguments` object is
what the CLI builds and hands to the check dispatch in ``compwa_policy.cli._checks``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from attrs import field, frozen

if TYPE_CHECKING:
    from compwa_policy.config import PythonVersion, TypeChecker
    from compwa_policy.env.conda import PackageManagerChoice
    from compwa_policy.github import upgrade_lock


TomlFormatter = Literal["taplo", "tombi"]
"""TOML formatters supported by the policy framework."""


@frozen
class Arguments:
    """Resolved configuration shared by every check.

    The :program:`policy` CLI constructs this from its options (see
    ``compwa_policy.cli._options.build_arguments``).
    """

    allow_deprecated_workflows: bool
    allow_labels: bool
    allow_vscode_coverage_gutters: bool
    allowed_cell_metadata: str
    branch_coverage: bool
    ci_skipped_tests: str
    dev_python_version: PythonVersion
    doc_apt_packages: str
    environment_variables: str
    excluded_python_versions: set[PythonVersion]
    github_pages: bool
    gitpod: bool
    imports_on_top: bool
    keep_contributing_md: bool
    keep_issue_templates: bool
    keep_pr_linting: bool
    keep_workflow: set[str] = field(converter=set)
    macos_python_version: PythonVersion | None
    no_binder: bool
    no_cd: bool
    no_cspell_update: bool
    no_github_actions: bool
    no_milestones: bool
    no_pypi: bool
    no_ruff: bool
    no_version_branches: bool
    package_manager: PackageManagerChoice
    pytest_single_threaded: bool
    python: bool | None
    repo_name: str
    repo_organization: str
    repo_title: str
    toml_formatter: TomlFormatter
    type_checker: set[TypeChecker]
    upgrade_frequency: upgrade_lock.Frequency


def _get_environment_variables(arg: str) -> dict[str, str]:
    """Create a dictionary of environment variables from a string argument.

    >>> _get_environment_variables("A=1, B=2")
    {'A': '1', 'B': '2'}
    >>> _get_environment_variables("A=1 B=2")
    {'A': '1', 'B': '2'}
    >>> _get_environment_variables("A=1")
    {'A': '1'}
    >>> _get_environment_variables("A=1,")
    {'A': '1'}
    >>> _get_environment_variables("A=1, B=2,")
    {'A': '1', 'B': '2'}
    >>> _get_environment_variables("A=1, B=2, ")
    {'A': '1', 'B': '2'}
    >>> _get_environment_variables("A=1, B=2, C=3")
    {'A': '1', 'B': '2', 'C': '3'}
    >>> _get_environment_variables("A=1, B=2, C=3,")
    {'A': '1', 'B': '2', 'C': '3'}
    >>> _get_environment_variables("A=1, B=2, C=3, ")
    {'A': '1', 'B': '2', 'C': '3'}
    >>> _get_environment_variables("A=1, B=2, C=3, D=4")
    {'A': '1', 'B': '2', 'C': '3', 'D': '4'}
    """
    if not arg:
        return {}
    return dict(
        pair.split("=")
        for pair in arg.replace(",", " ").split()
        if pair and "=" in pair
    )


def _to_list(arg: str) -> list[str]:
    """Create a comma-separated list from a string argument.

    >>> _to_list("a c , test,b")
    ['a', 'b', 'c', 'test']
    >>> _to_list("d")
    ['d']
    >>> _to_list(" ")
    []
    >>> _to_list("")
    []
    """
    space_separated = arg.replace(",", " ")
    while "  " in space_separated:
        space_separated = space_separated.replace("  ", " ")
    if space_separated in {"", " "}:
        return []
    return sorted(space_separated.split(" "))
