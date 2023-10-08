"""A collection of scripts that check the file structure of a repository."""

import sys
from argparse import ArgumentParser
from typing import List, Optional, Sequence

from repoma.check_dev_files.deprecated import remove_deprecated_tools
from repoma.utilities.executor import Executor

from . import (
    black,
    citation,
    commitlint,
    cspell,
    editorconfig,
    github_labels,
    github_workflows,
    gitpod,
    mypy,
    nbstripout,
    precommit,
    prettier,
    pyright,
    pytest,
    pyupgrade,
    release_drafter,
    ruff,
    setup_cfg,
    toml,
    update_pip_constraints,
    vscode,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _create_argparse()
    args = parser.parse_args(argv)
    is_python_repo = not args.no_python
    if not args.repo_title:
        args.repo_title = args.repo_name
    has_notebooks = not args.no_notebooks
    executor = Executor()
    executor(citation.main)
    executor(commitlint.main)
    executor(cspell.main)
    executor(editorconfig.main, args.no_python)
    if not args.allow_labels:
        executor(github_labels.main)
    if not args.no_github_actions:
        executor(
            github_workflows.main,
            allow_deprecated=args.allow_deprecated_workflows,
            doc_apt_packages=_to_list(args.doc_apt_packages),
            no_macos=args.no_macos,
            no_pypi=args.no_pypi,
            no_version_branches=args.no_version_branches,
            single_threaded=args.pytest_single_threaded,
            skip_tests=_to_list(args.ci_skipped_tests),
            test_extras=_to_list(args.ci_test_extras),
        )
    executor(nbstripout.main)
    executor(toml.main)  # has to run before pre-commit
    executor(prettier.main, args.no_prettierrc)
    if is_python_repo:
        executor(black.main, has_notebooks)
        if not args.no_github_actions:
            executor(release_drafter.main, args.repo_name, args.repo_title)
        if args.pin_requirements != "no":
            executor(
                update_pip_constraints.main,
                cron_frequency=args.pin_requirements,
            )
        executor(mypy.main)
        executor(pyright.main)
        executor(pytest.main)
        executor(pyupgrade.main)
        if not args.no_ruff:
            executor(ruff.main)
        executor(setup_cfg.main, args.ignore_author)
    executor(remove_deprecated_tools, args.keep_issue_templates)
    executor(vscode.main, has_notebooks)
    executor(gitpod.main, args.no_gitpod)
    executor(precommit.main)
    return executor.finalize(exception=False)


def _create_argparse() -> ArgumentParser:
    parser = ArgumentParser(__doc__)
    parser.add_argument(
        "--allow-deprecated-workflows",
        action="store_true",
        default=False,
        help="Allow deprecated CI workflows, such as ci-docs.yml.",
    )
    parser.add_argument(
        "--ci-skipped-tests",
        default="",
        help="Avoid running CI test on the following Python versions",
        required=False,
        type=str,
    )
    parser.add_argument(
        "--ci-test-extras",
        default="",
        help="Comma-separated list of extras that are required for running tests on CI",
        required=False,
        type=str,
    )
    parser.add_argument(
        "--doc-apt-packages",
        default="",
        help=(
            "Comma- or space-separated list of APT packages that are required to build"
            " documentation"
        ),
        required=False,
        type=str,
    )
    parser.add_argument(
        "--keep-issue-templates",
        help="Do not remove the .github/ISSUE_TEMPLATE directory",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--ignore-author",
        action="store_true",
        default=False,
        help="Do not update author info in setup.cfg.",
    )
    parser.add_argument(
        "--no-github-actions",
        action="store_true",
        default=False,
        help="Skip check that concern config files for Python projects.",
    )
    parser.add_argument(
        "--no-python",
        action="store_true",
        default=False,
        help="Skip check that concern config files for Python projects.",
    )
    parser.add_argument(
        "--no-gitpod",
        action="store_true",
        default=False,
        help="Do not create a GitPod config file",
    )
    parser.add_argument(
        "--no-prettierrc",
        action="store_true",
        default=False,
        help="Remove the prettierrc, so that Prettier's default values are used.",
    )
    parser.add_argument(
        "--allow-labels",
        action="store_true",
        default=False,
        help="Do not perform the check on labels.toml",
    )
    parser.add_argument(
        "--no-macos",
        action="store_true",
        default=False,
        help="Do not run test job on macOS",
    )
    parser.add_argument(
        "--no-notebooks",
        action="store_true",
        default=False,
        help="This repository does not contain Jupyter notebooks",
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
        "--pin-requirements",
        choices=["no", "biweekly", "monthly", "bimonthly"],
        default="no",
        help=(
            "Add a script to pin developer requirements to a constraint file."
            " Argument is the frequency of the cron job"
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
        help=(
            "Name of the repository. This can usually be found in the URL of the"
            " repository on GitHub or GitLab"
        ),
        required=True,
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


def _to_list(arg: str) -> List[str]:
    """Create a comma-separated list from a string argument.

    >>> _to_list('a c , test,b')
    ['a', 'b', 'c', 'test']
    >>> _to_list(' ')
    []
    >>> _to_list('')
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
