"""Reusable Typer option definitions shared by the :program:`policy` subcommands.

Each option is defined exactly once as an :class:`~typing.Annotated` alias and reused
across the grouped subcommands and the run-all callback. The actual checks live under
the sub-modules of `compwa_policy` and are unaffected by this layer; only the option
parsing and dispatch are organized here.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING, Annotated

import typer

from compwa_policy import Arguments, TomlFormatter, _to_list
from compwa_policy.cli._settings import load_settings
from compwa_policy.config import (
    DEFAULT_DEV_PYTHON_VERSION,
    PackageManagerChoice,
    PythonVersion,
)
from compwa_policy.config import UpgradeFrequency as Frequency

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
    PythonVersion | None,
    typer.Option(
        "--dev-python-version",
        show_default=DEFAULT_DEV_PYTHON_VERSION,
        help="Specify the Python version for your developer environment.",
    ),
]
PackageManager = Annotated[
    PackageManagerChoice | None,
    typer.Option(
        "--package-manager",
        show_default="uv",
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
    str | None,
    typer.Option(
        "--repo-name",
        help=(
            "Name of the repository. This can usually be found in the URL of the"
            " repository on GitHub or GitLab."
        ),
    ),
]
RepoOrganization = Annotated[
    str | None,
    typer.Option(
        "--repo-organization",
        show_default="ComPWA",
        help="Name of the organization under which the repository lives.",
    ),
]
RepoTitle = Annotated[
    str | None,
    typer.Option(
        "--repo-title",
        help=(
            "Title or full name of the repository. If not provided, this falls back to"
            " the repo-name."
        ),
    ),
]
EnvironmentVariables = Annotated[
    str | None,
    typer.Option(
        "--environment-variables",
        help="Comma- or space-separated list of environment variables, e.g. PYTHONHASHSEED=0,SKIP=pyright.",
    ),
]

# Python group ----------------------------------------------------------------
ExcludedPythonVersions = Annotated[
    str | None,
    typer.Option(
        "--excluded-python-versions",
        help="Comma- or space-separated list of Python versions you do NOT want to support.",
    ),
]
NoRuff = Annotated[
    bool | None,
    typer.Option("--no-ruff", help="Do not enforce Ruff as a linter."),
]
ImportsOnTop = Annotated[
    bool | None,
    typer.Option("--imports-on-top", help="Sort notebook imports on the top."),
]
BranchCoverage = Annotated[
    bool | None,
    typer.Option(
        "--branch-coverage/--no-branch-coverage",
        help="Enable branch coverage in the Coverage.py pytest configuration.",
    ),
]
TypeCheckerOption = Annotated[
    list[TypeChecker] | None,
    typer.Option(
        "--type-checker", help="Specify which type checker to use for the project."
    ),
]
PytestSingleThreaded = Annotated[
    bool | None,
    typer.Option(
        "--pytest-single-threaded", help="Run pytest without the `-n` argument."
    ),
]
AllowVscodeCoverageGutters = Annotated[
    bool | None,
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
    bool | None,
    typer.Option("--allow-labels", help="Do not perform the check on labels.toml."),
]
AllowDeprecatedWorkflows = Annotated[
    bool | None,
    typer.Option(
        "--allow-deprecated-workflows",
        help="Allow deprecated CI workflows, such as ci-docs.yml.",
    ),
]
NoGithubActions = Annotated[
    bool | None,
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
    bool | None,
    typer.Option("--github-pages", help="Host documentation on GitHub Pages."),
]
KeepPrLinting = Annotated[
    bool | None,
    typer.Option("--keep-pr-linting", help="Do not overwrite the PR linting workflow."),
]
MacosPythonVersion = Annotated[
    str | None,
    typer.Option(
        "--macos-python-version",
        show_default="3.10",
        help="Run the test job in MacOS on a specific Python version. Use 'disable' to not run the tests on MacOS.",
    ),
]
NoCd = Annotated[
    bool | None,
    typer.Option(
        "--no-cd", help="Do not add any GitHub workflows for continuous deployment."
    ),
]
NoMilestones = Annotated[
    bool | None,
    typer.Option(
        "--no-milestones",
        help="This repository does not use milestones and therefore no close workflow.",
    ),
]
NoPypi = Annotated[
    bool | None,
    typer.Option("--no-pypi", help="Do not publish package to PyPI."),
]
NoVersionBranches = Annotated[
    bool | None,
    typer.Option(
        "--no-version-branches",
        help="Do not push to matching major/minor version branches upon tagging.",
    ),
]
CiSkippedTests = Annotated[
    str | None,
    typer.Option(
        "--ci-skipped-tests",
        help="Avoid running CI test on the following Python versions.",
    ),
]
DocAptPackages = Annotated[
    str | None,
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
    Frequency | None,
    typer.Option(
        "--upgrade-frequency",
        show_default="quarterly",
        help=(
            "Add a workflow to upgrade lock files, like uv.lock,"
            " .pre-commit-config.yml, and pip .constraints/ files. The argument is the"
            " frequency of the cron job."
        ),
    ),
]

# Notebook group --------------------------------------------------------------
NoBinder = Annotated[
    bool | None,
    typer.Option("--no-binder", help="Do not update the Binder configuration."),
]
AllowedCellMetadata = Annotated[
    str | None,
    typer.Option(
        "--allowed-cell-metadata",
        help="Comma-separated list of allowed metadata in Jupyter notebook cells, e.g. editable,slideshow.",
    ),
]

# Format group ----------------------------------------------------------------
TombiErrorsOnWarnings = Annotated[
    bool | None,
    typer.Option(
        "--tombi-errors-on-warnings/--no-tombi-errors-on-warnings",
        help="Make the Tombi lint hook fail when it emits warnings.",
    ),
]
TomlFormatterOption = Annotated[
    TomlFormatter | None,
    typer.Option(
        "--toml-formatter",
        show_default="tombi",
        help="Choose the TOML formatter",
    ),
]
NoCspellUpdate = Annotated[
    bool | None,
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
    bool | None,
    typer.Option("--gitpod", help="Create a GitPod config file."),
]
KeepContributingMd = Annotated[
    bool | None,
    typer.Option(
        "--keep-contributing-md",
        help="Do not update or remove the CONTRIBUTING.md file.",
    ),
]
KeepIssueTemplates = Annotated[
    bool | None,
    typer.Option(
        "--keep-issue-templates",
        help="Do not remove the .github/ISSUE_TEMPLATE directory.",
    ),
]


def build_arguments(**overrides: Any) -> Arguments:
    """Create an :class:`.Arguments` object from the CLI and :code:`pyproject.toml`.

    Subcommands only expose the options relevant to them; every other field falls back
    to the ``[tool.compwa.policy]`` table (if present) and then to the same default that
    the ``check-dev-files`` hook uses. See the ``_settings`` for the resolution order.
    """
    settings = load_settings(**overrides).model_dump()
    settings["excluded_python_versions"] = set(
        _to_list(settings["excluded_python_versions"])
    )
    if settings["macos_python_version"] == "disable":
        settings["macos_python_version"] = None
    settings["repo_name"] = settings["repo_name"] or os.path.basename(os.getcwd())
    settings["repo_title"] = settings["repo_title"] or settings["repo_name"]
    settings["type_checker"] = set(settings["type_checker"])
    return Arguments(**settings)
