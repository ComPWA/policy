"""``policy github`` — workflows, labels, dependabot, release-drafter, upgrade-lock."""

from __future__ import annotations

from compwa_policy.check_dev_files.cli import _checks
from compwa_policy.check_dev_files.cli._options import (
    AllowDeprecatedWorkflows,
    AllowLabels,
    CiSkippedTests,
    DevPythonVersion,
    DocAptPackages,
    EnvironmentVariables,
    GithubPages,
    KeepPrLinting,
    KeepWorkflow,
    MacosPythonVersion,
    NoCd,
    NoGithubActions,
    NoMilestones,
    NoPypi,
    NoVersionBranches,
    PytestSingleThreaded,
    Python,
    RepoName,
    RepoOrganization,
    RepoTitle,
    UpgradeFrequency,
    build_arguments,
)


def github(  # noqa: PLR0917
    python: Python = None,
    dev_python_version: DevPythonVersion = "3.13",
    allow_labels: AllowLabels = False,
    no_github_actions: NoGithubActions = False,
    allow_deprecated_workflows: AllowDeprecatedWorkflows = False,
    github_pages: GithubPages = False,
    keep_pr_linting: KeepPrLinting = False,
    macos_python_version: MacosPythonVersion = "3.10",
    no_cd: NoCd = False,
    no_milestones: NoMilestones = False,
    no_pypi: NoPypi = False,
    no_version_branches: NoVersionBranches = False,
    ci_skipped_tests: CiSkippedTests = "",
    doc_apt_packages: DocAptPackages = "",
    environment_variables: EnvironmentVariables = "",
    pytest_single_threaded: PytestSingleThreaded = False,
    keep_workflow: KeepWorkflow = None,
    upgrade_frequency: UpgradeFrequency = "quarterly",
    repo_name: RepoName = "",
    repo_organization: RepoOrganization = "ComPWA",
    repo_title: RepoTitle = "",
) -> None:
    """Standardize GitHub config: workflows, labels, Dependabot, Release Drafter, lock upgrades."""
    args = build_arguments(
        python=python,
        dev_python_version=dev_python_version,
        allow_labels=allow_labels,
        no_github_actions=no_github_actions,
        allow_deprecated_workflows=allow_deprecated_workflows,
        github_pages=github_pages,
        keep_pr_linting=keep_pr_linting,
        macos_python_version=macos_python_version,
        no_cd=no_cd,
        no_milestones=no_milestones,
        no_pypi=no_pypi,
        no_version_branches=no_version_branches,
        ci_skipped_tests=ci_skipped_tests,
        doc_apt_packages=doc_apt_packages,
        environment_variables=environment_variables,
        pytest_single_threaded=pytest_single_threaded,
        keep_workflow=keep_workflow,
        upgrade_frequency=upgrade_frequency,
        repo_name=repo_name,
        repo_organization=repo_organization,
        repo_title=repo_title,
    )
    _checks.dispatch(args, "github")
