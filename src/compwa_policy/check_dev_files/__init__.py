"""A collection of scripts that check the file structure of a repository."""

from __future__ import annotations

import os
import re
import sys
from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING, Any

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
    tox,
    update_lock,
    uv,
    vscode,
)
from compwa_policy.check_dev_files.deprecated import remove_deprecated_tools
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import git_ls_files, matches_patterns
from compwa_policy.utilities.precommit import ModifiablePrecommit

if TYPE_CHECKING:
    from collections.abc import Sequence

    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.utilities.pyproject import PythonVersion


def main(argv: Sequence[str] | None = None) -> int:  # noqa: PLR0915
    parser = _create_argparse()
    args = parser.parse_args(argv)
    doc_apt_packages = _to_list(args.doc_apt_packages)
    environment_variables = _get_environment_variables(args.environment_variables)
    is_python_repo = not args.no_python
    repo_name, repo_title = _determine_repo_name_and_title(args)
    has_notebooks = any(
        matches_patterns(file, ["**/*.ipynb"]) for file in git_ls_files(untracked=True)
    )
    use_gitpod = args.gitpod
    dev_python_version = __get_python_version(args.dev_python_version)
    package_manager: PackageManagerChoice = args.package_manager
    with (
        Executor(raise_exception=False) as do,
        ModifiablePrecommit.load() as precommit_config,
    ):
        do(citation.main, precommit_config)
        do(commitlint.main)
        do(conda.main, dev_python_version, package_manager)
        do(dependabot.main, args.dependabot)
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
                no_cd=args.no_cd,
                no_macos=args.no_macos,
                no_milestones=args.no_milestones,
                no_pypi=args.no_pypi,
                no_version_branches=args.no_version_branches,
                python_version=dev_python_version,
                single_threaded=args.pytest_single_threaded,
                skip_tests=_to_list(args.ci_skipped_tests),
                test_extras=_to_list(args.ci_test_extras),
            )
        if has_notebooks:
            if not args.no_binder:
                do(binder.main, package_manager, dev_python_version, doc_apt_packages)
            do(jupyter.main, args.no_ruff)
        do(nbstripout.main, precommit_config, _to_list(args.allowed_cell_metadata))
        do(
            pixi.main,
            package_manager,
            is_python_repo,
            dev_python_version,
            args.outsource_pixi_to_tox,
        )
        do(tox.main, has_notebooks)
        do(direnv.main, package_manager, environment_variables)
        do(toml.main, precommit_config)  # has to run before pre-commit
        do(prettier.main, precommit_config)
        if is_python_repo:
            if args.no_ruff:
                do(black.main, precommit_config, has_notebooks)
            if not args.no_github_actions:
                do(
                    release_drafter.main,
                    args.no_cd,
                    repo_name,
                    repo_title,
                    args.repo_organization,
                )
            do(mypy.main)
            do(pyproject.main, args.excluded_python_versions, no_pypi=args.no_pypi)
            do(pyright.main, package_manager, precommit_config)
            do(pytest.main)
            do(pyupgrade.main, precommit_config, args.no_ruff)
            if not args.no_ruff:
                do(ruff.main, precommit_config, has_notebooks, args.imports_on_top)
        if args.update_lock_files != "no":
            do(
                update_lock.main,
                precommit_config,
                frequency=args.update_lock_files,
            )
        do(readthedocs.main, package_manager, dev_python_version)
        do(remove_deprecated_tools, precommit_config, args.keep_issue_templates)
        do(vscode.main, has_notebooks, is_python_repo)
        do(gitpod.main, use_gitpod, dev_python_version)
        do(precommit.main, precommit_config, has_notebooks)
        do(
            uv.main,
            dev_python_version,
            package_manager,
            precommit_config,
            args.repo_organization,
            repo_name,
        )
        do(cspell.main, precommit_config, args.no_cspell_update)
    return 1 if do.error_messages else 0


def _create_argparse() -> ArgumentParser:
    parser = ArgumentParser(__doc__)
    parser.add_argument(
        "--allow-deprecated-workflows",
        action="store_true",
        default=False,
        help="Allow deprecated CI workflows, such as ci-docs.yml.",
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
        "--ci-test-extras",
        default="",
        help="Comma-separated list of extras that are required for running tests on CI",
        type=str,
    )
    parser.add_argument(
        "--dependabot",
        choices=dependabot.DependabotOption.__args__,  # type: ignore[attr-defined]
        default=None,
        help="Leave dependabot.yml untouched ('keep') or sync with ComPWA/policy",
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
        "--outsource-pixi-to-tox",
        action="store_true",
        default=False,
        help="Run tox command through pixi",
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
        "--allow-labels",
        action="store_true",
        default=False,
        help="Do not perform the check on labels.toml",
    )
    parser.add_argument(
        "--dev-python-version",
        default="3.12",
        help="Specify the Python version for your developer environment",
        type=str,
    )
    parser.add_argument(
        "--no-macos",
        action="store_true",
        default=False,
        help="Do not run test job on macOS",
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
        choices=sorted(conda.PackageManagerChoice.__args__),  # type:ignore[attr-defined]
        default="uv",
        help="Specify which package manager to use for the project",
        type=str,
    )
    parser.add_argument(
        "--update-lock-files",
        choices=update_lock.Frequency.__args__,  # type:ignore[attr-defined]
        default="outsource",
        help=(
            "Add a workflow to update lock files, like uv.lock, .pre-commit-config.yml, "
            "and pip .constraints/ files. The argument is the frequency of the cron job"
        ),
        type=str,
    )
    parser.add_argument(
        "--pytest-single-threaded",
        action="store_true",
        default=False,
        help="Run pytest without the `-n` argument",
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
    return parser


def _determine_repo_name_and_title(args: Namespace) -> tuple[str, str]:
    repo_name = args.repo_name
    if not repo_name:
        repo_name = os.path.basename(os.getcwd())
    repo_title = args.repo_title or repo_name
    return repo_name, repo_title


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


def __get_python_version(arg: Any) -> PythonVersion:
    if not isinstance(arg, str):
        msg = f"--dev-python-version must be a string, not {type(arg).__name__}"
        raise TypeError(msg)
    arg = arg.strip()
    if not re.match(r"^3\.\d+$", arg):
        msg = f"Invalid Python version: {arg}"
        raise ValueError(msg)
    return arg  # type: ignore[return-value]


if __name__ == "__main__":
    sys.exit(main())
