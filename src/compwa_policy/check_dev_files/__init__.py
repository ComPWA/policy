"""A collection of scripts that check the file structure of a repository."""

from __future__ import annotations

import os
import sys
from argparse import ArgumentParser
from typing import TYPE_CHECKING

from attrs import frozen

from compwa_policy.check_dev_files import (
    binder,
    black,
    citation,
    commitlint,
    conda,
    cspell,
    dependabot,
    direnv,
    editorconfig,
    github_labels,
    github_workflows,
    gitpod,
    jupyter,
    mypy,
    nbstripout,
    pixi,
    poe,
    precommit,
    prettier,
    pyproject,
    pyright,
    pytest,
    pyupgrade,
    readthedocs,
    release_drafter,
    ruff,
    toml,
    ty,
    upgrade_lock,
    uv,
    vscode,
)
from compwa_policy.check_dev_files.deprecated import remove_deprecated_tools
from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION, PythonVersion
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import Pyproject

if TYPE_CHECKING:
    from collections.abc import Sequence

    from compwa_policy.check_dev_files.conda import PackageManagerChoice


def main(argv: Sequence[str] | None = None) -> int:  # noqa: C901, PLR0915
    args = _create_argparse(argv)
    doc_apt_packages = _to_list(args.doc_apt_packages)
    environment_variables = _get_environment_variables(args.environment_variables)
    is_python_repo = not args.no_python
    has_notebooks = is_committed("**/*.ipynb")
    if CONFIG_PATH.pyproject.exists():
        supported_versions = Pyproject.load().get_supported_python_versions()
        if supported_versions and args.dev_python_version not in supported_versions:
            print(  # noqa: T201
                f"The specified development Python version {args.dev_python_version} is"
                " not listed in the supported Python versions of pyproject.toml:"
                f" {', '.join(sorted(supported_versions))}"
            )
            return 1
    with (
        Executor(raise_exception=False) as do,
        ModifiablePrecommit.load() as precommit_config,
    ):
        do(citation.main, precommit_config)
        do(commitlint.main)
        do(conda.main, args.dev_python_version, args.package_manager)
        do(dependabot.main, args.upgrade_frequency)
        do(editorconfig.main, precommit_config)
        if not args.allow_labels:
            do(github_labels.main)
        if not args.no_github_actions:
            do(
                github_workflows.main,
                precommit_config,
                allow_deprecated=args.allow_deprecated_workflows,
                doc_apt_packages=doc_apt_packages,
                environment_variables=environment_variables,
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
        if has_notebooks:
            if not args.no_binder:
                do(
                    binder.main,
                    args.package_manager,
                    args.dev_python_version,
                    doc_apt_packages,
                )
            do(jupyter.main, args.no_ruff)
        do(
            nbstripout.main,
            precommit_config,
            has_notebooks,
            _to_list(args.allowed_cell_metadata),
        )
        do(
            pixi.main,
            args.package_manager,
            is_python_repo,
            args.dev_python_version,
        )
        do(direnv.main, args.package_manager, environment_variables)
        do(toml.main, precommit_config)  # has to run before pre-commit
        do(poe.main, has_notebooks, args.package_manager)
        do(prettier.main, precommit_config)
        if is_python_repo:
            if args.no_ruff:
                do(black.main, precommit_config, has_notebooks)
            if not args.no_github_actions:
                do(
                    release_drafter.main,
                    args.no_cd,
                    args.repo_name,
                    args.repo_title,
                    args.repo_organization,
                )
            do(pyproject.main, args.excluded_python_versions)
            do(mypy.main, "mypy" in args.type_checker, precommit_config)
            do(pyright.main, "pyright" in args.type_checker, precommit_config)
            do(ty.main, args.type_checker, args.keep_local_precommit, precommit_config)
            do(pytest.main, args.pytest_single_threaded)
            do(pyupgrade.main, precommit_config, args.no_ruff)
            if not args.no_ruff:
                do(ruff.main, precommit_config, has_notebooks, args.imports_on_top)
        if args.upgrade_frequency != "no":
            do(
                upgrade_lock.main,
                precommit_config,
                frequency=args.upgrade_frequency,
            )
        do(readthedocs.main, args.package_manager, args.dev_python_version)
        do(remove_deprecated_tools, precommit_config, args.keep_issue_templates)
        do(vscode.main, has_notebooks, is_python_repo, args.package_manager)
        do(gitpod.main, args.gitpod, args.dev_python_version)
        do(precommit.main, precommit_config, has_notebooks)
        do(
            uv.main,
            precommit_config,
            args.dev_python_version,
            args.package_manager,
            args.repo_organization,
            args.repo_name,
        )
        do(cspell.main, precommit_config, args.no_cspell_update)
    return 1 if do.error_messages else 0


def _create_argparse(argv: Sequence[str] | None = None) -> Arguments:
    parser = ArgumentParser(__doc__)
    parser.add_argument(
        "--allow-deprecated-workflows",
        action="store_true",
        default=False,
        help="Allow deprecated CI workflows, such as ci-docs.yml.",
    )
    parser.add_argument(
        "--allow-labels",
        action="store_true",
        default=False,
        help="Do not perform the check on labels.toml",
    )
    parser.add_argument(
        "--allowed-cell-metadata",
        default="",
        help="Comma-separated list of allowed metadata in Jupyter notebook cells, e.g. editable,slideshow.",
        type=str,
    )
    parser.add_argument(
        "--ci-skipped-tests",
        default="",
        help="Avoid running CI test on the following Python versions",
        type=str,
    )
    parser.add_argument(
        "--dev-python-version",
        choices=PythonVersion.__args__,
        default=DEFAULT_DEV_PYTHON_VERSION,
        help="Specify the Python version for your developer environment",
    )
    parser.add_argument(
        "--doc-apt-packages",
        default="",
        help="Comma- or space-separated list of APT packages that are required to build documentation",
        type=str,
    )
    parser.add_argument(
        "--environment-variables",
        default="",
        help="Comma- or space-separated list of environment variables, e.g. PYTHONHASHSEED=0,SKIP=pyright",
        type=str,
    )
    parser.add_argument(
        "--excluded-python-versions",
        default="",
        help="Comma- or space-separated list of Python versions you do NOT want to support",
        type=str,
    )
    parser.add_argument(
        "--github-pages",
        action="store_true",
        default=False,
        help="Host documentation on GitHub Pages",
    )
    parser.add_argument(
        "--gitpod",
        action="store_true",
        default=False,
        help="Create a GitPod config file",
    )
    parser.add_argument(
        "--keep-issue-templates",
        help="Do not remove the .github/ISSUE_TEMPLATE directory",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--keep-pr-linting",
        help="Do not overwrite the PR linting workflow",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--imports-on-top",
        action="store_true",
        default=False,
        help="Sort notebook imports on the top",
    )
    parser.add_argument(
        "--no-binder",
        action="store_true",
        default=False,
        help="Do not update the Binder configuration",
    )
    parser.add_argument(
        "--no-cd",
        action="store_true",
        default=False,
        help="Do not add any GitHub workflows for continuous deployment",
    )
    parser.add_argument(
        "--no-cspell-update",
        action="store_true",
        default=False,
        help=(
            "Do not enforce same cSpell configuration as other ComPWA repositories."
            " This can be useful if you have a more advanced configuration, like using"
            " different dictionaries for different file types."
        ),
    )
    parser.add_argument(
        "--no-github-actions",
        action="store_true",
        default=False,
        help=(
            "Do not add standard GitHub Actions workflows that are used across ComPWA"
            " repositories. This can be useful if you already have your own CI"
            " workflows that do the same as the workflows enforced by the"
            " check-dev-files hook."
        ),
    )
    parser.add_argument(
        "--no-milestones",
        action="store_true",
        default=False,
        help="This repository does not use milestones and therefore no close workflow.",
    )
    parser.add_argument(
        "--no-python",
        action="store_true",
        default=False,
        help="Skip check that concern config files for Python projects.",
    )
    parser.add_argument(
        "--keep-local-precommit",
        action="store_true",
        default=False,
        help="Do not remove local pre-commit hooks",
    )
    parser.add_argument(
        "--macos-python-version",
        choices=[*sorted(PythonVersion.__args__), "disable"],
        default="3.10",
        help="Run the test job in MacOS on a specific Python version. Use 'disable' to not run the tests on MacOS.",
    )
    parser.add_argument(
        "--no-pypi",
        action="store_true",
        default=False,
        help="Do not publish package to PyPI",
    )
    parser.add_argument(
        "--no-ruff",
        action="store_true",
        default=False,
        help="Do not enforce Ruff as a linter",
    )
    parser.add_argument(
        "--no-version-branches",
        action="store_true",
        default=False,
        help="Do not push to matching major/minor version branches upon tagging",
    )
    parser.add_argument(
        "--package-manager",
        choices=sorted(conda.PackageManagerChoice.__args__),
        default="uv",
        help="Specify which package manager to use for the project",
        type=str,
    )
    parser.add_argument(
        "--pytest-single-threaded",
        action="store_true",
        default=False,
        help="Run pytest without the `-n` argument",
    )
    parser.add_argument(
        "--type-checker",
        action="append",
        choices=ty.TypeChecker.__args__,
        help="Specify which type checker to use for the project",
    )
    parser.add_argument(
        "--upgrade-frequency",
        choices=upgrade_lock.Frequency.__args__,
        default="quarterly",
        help=(
            "Add a workflow to upgrade lock files, like uv.lock, .pre-commit-config.yml, "
            "and pip .constraints/ files. The argument is the frequency of the cron job"
        ),
    )
    parser.add_argument(
        "--repo-name",
        default="",
        help=(
            "Name of the repository. This can usually be found in the URL of the"
            " repository on GitHub or GitLab"
        ),
        type=str,
    )
    parser.add_argument(
        "--repo-organization",
        default="ComPWA",
        help="Name of the organization under which the repository lives.",
        type=str,
    )
    parser.add_argument(
        "--repo-title",
        default="",
        help=(
            "Title or full name of the repository. If not provided, this falls back to"
            " the repo-name."
        ),
        type=str,
    )
    args = parser.parse_args(argv)
    args.excluded_python_versions = set(_to_list(args.excluded_python_versions))
    args.macos_python_version = (
        None if args.macos_python_version == "disable" else args.macos_python_version
    )
    args.repo_name = args.repo_name or os.path.basename(os.getcwd())
    args.repo_title = args.repo_title or args.repo_name
    args.type_checker = set(args.type_checker or [])
    return Arguments(**args.__dict__)


@frozen
class Arguments:
    allow_deprecated_workflows: bool
    allow_labels: bool
    allowed_cell_metadata: str
    ci_skipped_tests: str
    dev_python_version: PythonVersion
    doc_apt_packages: str
    environment_variables: str
    excluded_python_versions: set[PythonVersion]
    github_pages: bool
    gitpod: bool
    imports_on_top: bool
    keep_issue_templates: bool
    keep_local_precommit: bool
    keep_pr_linting: bool
    macos_python_version: PythonVersion | None
    no_binder: bool
    no_cd: bool
    no_cspell_update: bool
    no_github_actions: bool
    no_milestones: bool
    no_pypi: bool
    no_python: bool
    no_ruff: bool
    no_version_branches: bool
    package_manager: PackageManagerChoice
    pytest_single_threaded: bool
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


if __name__ == "__main__":
    sys.exit(main())
