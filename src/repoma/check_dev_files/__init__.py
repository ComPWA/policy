"""A collection of scripts that check the file structure of a repository."""

import argparse
import sys
from typing import List, Optional, Sequence

from repoma.utilities.executor import Executor

from . import (
    black,
    commitlint,
    cspell,
    editorconfig,
    flake8,
    github_labels,
    github_templates,
    github_workflows,
    gitpod,
    nbstripout,
    precommit,
    prettier,
    pyupgrade,
    release_drafter,
    setup_cfg,
    toml,
    tox,
    update_pip_constraints,
    vscode,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
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
        "--ignore-author",
        action="store_true",
        default=False,
        help="Do not update author info in setup.cfg.",
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
        "--no-pypi",
        action="store_true",
        default=False,
        help="Do not publish package to PyPI",
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
    args = parser.parse_args(argv)
    is_python_repo = not args.no_python
    if not args.repo_title:
        args.repo_title = args.repo_name

    executor = Executor()
    executor(commitlint.main)
    executor(cspell.main)
    executor(editorconfig.main)
    if not args.allow_labels:
        executor(github_labels.main)
    executor(github_templates.main)
    executor(
        github_workflows.main,
        allow_deprecated=args.allow_deprecated_workflows,
        doc_apt_packages=_to_list(args.doc_apt_packages),
        no_macos=args.no_macos,
        no_pypi=args.no_pypi,
        skip_tests=_to_list(args.ci_skipped_tests),
        test_extras=_to_list(args.ci_test_extras),
    )
    if not args.no_gitpod:
        executor(gitpod.main)
    executor(nbstripout.main)
    executor(toml.main)  # has to run before pre-commit
    executor(precommit.main)
    executor(prettier.main, args.no_prettierrc)
    if is_python_repo:
        executor(black.main)
        executor(flake8.main)
        executor(release_drafter.main, args.repo_name, args.repo_title)
        if args.pin_requirements != "no":
            executor(
                update_pip_constraints.main,
                cron_frequency=args.pin_requirements,
            )
        executor(pyupgrade.main)
        executor(setup_cfg.main, args.ignore_author)
        executor(tox.main)
    executor(vscode.main)
    return executor.finalize(exception=False)


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
