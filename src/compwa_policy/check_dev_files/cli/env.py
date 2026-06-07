"""``policy env`` — uv, conda, pixi, direnv."""

from __future__ import annotations

from compwa_policy.check_dev_files.cli import _checks
from compwa_policy.check_dev_files.cli._options import (
    DevPythonVersion,
    EnvironmentVariables,
    KeepContributingMd,
    PackageManager,
    Python,
    RepoName,
    RepoOrganization,
    build_arguments,
)


def env(  # noqa: PLR0917
    python: Python = None,
    dev_python_version: DevPythonVersion = None,
    package_manager: PackageManager = None,
    environment_variables: EnvironmentVariables = None,
    keep_contributing_md: KeepContributingMd = None,
    repo_name: RepoName = None,
    repo_organization: RepoOrganization = None,
) -> None:
    """Standardize the developer environment: uv, Conda, Pixi, direnv."""
    args = build_arguments(
        python=python,
        dev_python_version=dev_python_version,
        package_manager=package_manager,
        environment_variables=environment_variables,
        keep_contributing_md=keep_contributing_md,
        repo_name=repo_name,
        repo_organization=repo_organization,
    )
    _checks.dispatch(args, "env")
