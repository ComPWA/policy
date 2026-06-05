"""Reusable Typer option definitions shared by the :program:`policy` subcommands.

Each option is defined exactly once as an :class:`~typing.Annotated` alias and reused
across the grouped subcommands and the run-all callback. The actual checks live in the
``compwa_policy.check_dev_files.*`` modules and are unaffected by this layer; only the
option parsing and dispatch are organized here.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING, Annotated

import typer

from compwa_policy.check_dev_files import Arguments, _to_list
from compwa_policy.check_dev_files.conda import PackageManagerChoice
from compwa_policy.check_dev_files.upgrade_lock import Frequency
from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION, PythonVersion

if TYPE_CHECKING:
    from typing import Any


class TypeChecker(str, Enum):
    """Type checkers that can be enabled with ``--type-checker``.

    Typer does not support ``list[Literal[...]]``, so the :data:`.ty.TypeChecker`
    literal is mirrored as an enum for the repeatable ``--type-checker`` option.
    """

    mypy = "mypy"
    pyright = "pyright"
    ty = "ty"


# Cross-cutting options -------------------------------------------------------
DevPythonVersion = Annotated[
    PythonVersion,
    typer.Option(
        "--dev-python-version",
        help="Specify the Python version for your developer environment.",
    ),
]
PackageManager = Annotated[
    PackageManagerChoice,
    typer.Option(
        "--package-manager",
        help="Specify which package manager to use for the project.",
    ),
]
Python = Annotated[
    bool | None,
    typer.Option(
        "--python/--no-python",
        help="Specify whether this repository contains Python code (default: automatic detection).",
    ),
]
RepoName = Annotated[
    str,
    typer.Option(
        "--repo-name",
        help=(
            "Name of the repository. This can usually be found in the URL of the"
            " repository on GitHub or GitLab."
        ),
    ),
]
RepoOrganization = Annotated[
    str,
    typer.Option(
        "--repo-organization",
        help="Name of the organization under which the repository lives.",
    ),
]
RepoTitle = Annotated[
    str,
    typer.Option(
        "--repo-title",
        help=(
            "Title or full name of the repository. If not provided, this falls back to"
            " the repo-name."
        ),
    ),
]
EnvironmentVariables = Annotated[
    str,
    typer.Option(
        "--environment-variables",
        help="Comma- or space-separated list of environment variables, e.g. PYTHONHASHSEED=0,SKIP=pyright.",
    ),
]

# Python group ----------------------------------------------------------------
ExcludedPythonVersions = Annotated[
    str,
    typer.Option(
        "--excluded-python-versions",
        help="Comma- or space-separated list of Python versions you do NOT want to support.",
    ),
]
NoRuff = Annotated[
    bool,
    typer.Option("--no-ruff", help="Do not enforce Ruff as a linter."),
]
ImportsOnTop = Annotated[
    bool,
    typer.Option("--imports-on-top", help="Sort notebook imports on the top."),
]
TypeCheckerOption = Annotated[
    list[TypeChecker] | None,
    typer.Option(
        "--type-checker", help="Specify which type checker to use for the project."
    ),
]
KeepLocalPrecommit = Annotated[
    bool,
    typer.Option(
        "--keep-local-precommit", help="Do not remove local pre-commit hooks."
    ),
]
PytestSingleThreaded = Annotated[
    bool,
    typer.Option(
        "--pytest-single-threaded", help="Run pytest without the `-n` argument."
    ),
]
AllowVscodeCoverageGutters = Annotated[
    bool,
    typer.Option(
        "--allow-vscode-coverage-gutters",
        help=(  # cspell:ignore ryanluker
            "Recommend the ryanluker.vscode-coverage-gutters extension and keep its"
            " settings, instead of marking it as an unwanted VS Code extension."
        ),
    ),
]

# GitHub group ----------------------------------------------------------------
AllowLabels = Annotated[
    bool,
    typer.Option("--allow-labels", help="Do not perform the check on labels.toml."),
]
AllowDeprecatedWorkflows = Annotated[
    bool,
    typer.Option(
        "--allow-deprecated-workflows",
        help="Allow deprecated CI workflows, such as ci-docs.yml.",
    ),
]
NoGithubActions = Annotated[
    bool,
    typer.Option(
        "--no-github-actions",
        help=(
            "Do not add standard GitHub Actions workflows that are used across ComPWA"
            " repositories. This can be useful if you already have your own CI"
            " workflows that do the same as the workflows enforced by the"
            " check-dev-files hook."
        ),
    ),
]
GithubPages = Annotated[
    bool,
    typer.Option("--github-pages", help="Host documentation on GitHub Pages."),
]
KeepPrLinting = Annotated[
    bool,
    typer.Option("--keep-pr-linting", help="Do not overwrite the PR linting workflow."),
]
MacosPythonVersion = Annotated[
    str,
    typer.Option(
        "--macos-python-version",
        help="Run the test job in MacOS on a specific Python version. Use 'disable' to not run the tests on MacOS.",
    ),
]
NoCd = Annotated[
    bool,
    typer.Option(
        "--no-cd", help="Do not add any GitHub workflows for continuous deployment."
    ),
]
NoMilestones = Annotated[
    bool,
    typer.Option(
        "--no-milestones",
        help="This repository does not use milestones and therefore no close workflow.",
    ),
]
NoPypi = Annotated[
    bool,
    typer.Option("--no-pypi", help="Do not publish package to PyPI."),
]
NoVersionBranches = Annotated[
    bool,
    typer.Option(
        "--no-version-branches",
        help="Do not push to matching major/minor version branches upon tagging.",
    ),
]
CiSkippedTests = Annotated[
    str,
    typer.Option(
        "--ci-skipped-tests",
        help="Avoid running CI test on the following Python versions.",
    ),
]
DocAptPackages = Annotated[
    str,
    typer.Option(
        "--doc-apt-packages",
        help="Comma- or space-separated list of APT packages that are required to build documentation.",
    ),
]
KeepWorkflow = Annotated[
    list[str] | None,
    typer.Option(
        "--keep-workflow",
        help="Names of the GitHub Actions workflows that should not be updated or removed, including the .yml extension.",
    ),
]
UpgradeFrequency = Annotated[
    Frequency,
    typer.Option(
        "--upgrade-frequency",
        help=(
            "Add a workflow to upgrade lock files, like uv.lock,"
            " .pre-commit-config.yml, and pip .constraints/ files. The argument is the"
            " frequency of the cron job."
        ),
    ),
]

# Notebook group --------------------------------------------------------------
NoBinder = Annotated[
    bool,
    typer.Option("--no-binder", help="Do not update the Binder configuration."),
]
AllowedCellMetadata = Annotated[
    str,
    typer.Option(
        "--allowed-cell-metadata",
        help="Comma-separated list of allowed metadata in Jupyter notebook cells, e.g. editable,slideshow.",
    ),
]

# Format group ----------------------------------------------------------------
NoCspellUpdate = Annotated[
    bool,
    typer.Option(
        "--no-cspell-update",
        help=(
            "Do not enforce same cSpell configuration as other ComPWA repositories."
            " This can be useful if you have a more advanced configuration, like using"
            " different dictionaries for different file types."
        ),
    ),
]

# Repo group ------------------------------------------------------------------
Gitpod = Annotated[
    bool,
    typer.Option("--gitpod", help="Create a GitPod config file."),
]
KeepContributingMd = Annotated[
    bool,
    typer.Option(
        "--keep-contributing-md",
        help="Do not update or remove the CONTRIBUTING.md file.",
    ),
]
KeepIssueTemplates = Annotated[
    bool,
    typer.Option(
        "--keep-issue-templates",
        help="Do not remove the .github/ISSUE_TEMPLATE directory.",
    ),
]

_DEFAULTS: dict[str, Any] = {
    "allow_deprecated_workflows": False,
    "allow_labels": False,
    "allow_vscode_coverage_gutters": False,
    "allowed_cell_metadata": "",
    "ci_skipped_tests": "",
    "dev_python_version": DEFAULT_DEV_PYTHON_VERSION,
    "doc_apt_packages": "",
    "environment_variables": "",
    "excluded_python_versions": "",
    "github_pages": False,
    "gitpod": False,
    "imports_on_top": False,
    "keep_contributing_md": False,
    "keep_issue_templates": False,
    "keep_local_precommit": False,
    "keep_pr_linting": False,
    "keep_workflow": [],
    "macos_python_version": "3.10",
    "no_binder": False,
    "no_cd": False,
    "no_cspell_update": False,
    "no_github_actions": False,
    "no_milestones": False,
    "no_pypi": False,
    "no_ruff": False,
    "no_version_branches": False,
    "package_manager": "uv",
    "pytest_single_threaded": False,
    "python": None,
    "repo_name": "",
    "repo_organization": "ComPWA",
    "repo_title": "",
    "type_checker": [],
    "upgrade_frequency": "quarterly",
}


def build_arguments(**overrides: Any) -> Arguments:
    """Create an :class:`.Arguments` object, applying the same post-processing as argparse.

    Subcommands only expose the options relevant to them; every other field falls back
    to the same default that the ``check-dev-files`` hook uses.
    """
    settings = {**_DEFAULTS, **{k: v for k, v in overrides.items() if v is not None}}
    settings["excluded_python_versions"] = set(
        _to_list(settings["excluded_python_versions"])
    )
    if settings["macos_python_version"] == "disable":
        settings["macos_python_version"] = None
    settings["repo_name"] = settings["repo_name"] or os.path.basename(os.getcwd())
    settings["repo_title"] = settings["repo_title"] or settings["repo_name"]
    settings["type_checker"] = {
        checker.value if isinstance(checker, TypeChecker) else checker
        for checker in settings["type_checker"] or []
    }
    return Arguments(**settings)
