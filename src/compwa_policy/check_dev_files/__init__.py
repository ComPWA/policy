"""A collection of scripts that check the file structure of a repository.

The command-line interface lives in :mod:`compwa_policy.check_dev_files.cli`. This
module only defines the shared `Arguments` data model and a few string helpers; the
`Arguments` object is what the CLI builds and hands to the check dispatch in
``compwa_policy.check_dev_files.cli._checks``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import field, frozen

if TYPE_CHECKING:
    from compwa_policy.check_dev_files import ty, upgrade_lock
    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.config import PythonVersion


@frozen
class Arguments:
    """Resolved configuration shared by every check.

    The :program:`policy` CLI constructs this from its options (see
    ``compwa_policy.check_dev_files.cli._options.build_arguments``).
    """

    allow_deprecated_workflows: bool
    allow_labels: bool
    allow_vscode_coverage_gutters: bool
    allowed_cell_metadata: str
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
    keep_local_precommit: bool
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
    type_checker: set[ty.TypeChecker]
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
