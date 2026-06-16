"""``policy repo`` — citation, commitlint, VS Code, GitPod, Poe, Read the Docs, deprecations."""

from __future__ import annotations

from compwa_policy.cli import _checks
from compwa_policy.cli._options import (
    DevPythonVersion,
    Gitpod,
    KeepIssueTemplates,
    PackageManager,
    Python,
    build_arguments,
)


def repo(
    python: Python = None,
    package_manager: PackageManager = None,
    dev_python_version: DevPythonVersion = None,
    gitpod: Gitpod = None,
    keep_issue_templates: KeepIssueTemplates = None,
) -> None:
    """Standardize miscellaneous repo files: citation, commitlint, VS Code, GitPod, Poe, Read the Docs."""
    args = build_arguments(
        python=python,
        package_manager=package_manager,
        dev_python_version=dev_python_version,
        gitpod=gitpod,
        keep_issue_templates=keep_issue_templates,
    )
    _checks.dispatch(args, "repo")
