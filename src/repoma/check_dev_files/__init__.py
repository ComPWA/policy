"""A collection of scripts that check the file structure of a repository."""

import argparse
import sys
from typing import Optional, Sequence

from repoma.utilities.executor import Executor

from . import (
    black,
    commitlint,
    cspell,
    editor_config,
    flake8,
    github_labels,
    github_templates,
    github_workflows,
    gitpod,
    nbstripout,
    prettier,
    pyupgrade,
    release_drafter,
    setup_cfg,
    tox,
    update_pip_constraints,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--ignore-author",
        default=False,
        action="store_true",
        help="Do not update author info in setup.cfg.",
    )
    parser.add_argument(
        "--no-python",
        default=False,
        action="store_true",
        help="Skip check that concern config files for Python projects.",
    )
    parser.add_argument(
        "--no-docs",
        default=False,
        action="store_true",
        help="Do not replace the ci-docs and linkcheck workflows.",
    )
    parser.add_argument(
        "--no-gitpod",
        default=False,
        action="store_true",
        help="Do not create a GitPod config file",
    )
    parser.add_argument(
        "--no-prettierrc",
        default=False,
        action="store_true",
        help="Remove the prettierrc, so that Prettier's default values are used.",
    )
    parser.add_argument(
        "--allow-labels",
        default=False,
        action="store_true",
        help="Do not perform the check on labels.toml",
    )
    parser.add_argument(
        "--no-cd",
        default=False,
        action="store_true",
        help="Do not update `cd.yml` workflow",
    )
    parser.add_argument(
        "--pin-requirements",
        choices=["no", "biweekly", "bimonthly"],
        default="no",
        help=(
            "Add a script to pin developer requirements to a constraint file."
            " Argument is the frequency of the cron job"
        ),
        type=str,
    )
    args = parser.parse_args(argv)
    is_python_repo = not args.no_python

    executor = Executor()
    executor(commitlint.main)
    executor(cspell.main)
    executor(editor_config.main)
    if not args.allow_labels:
        executor(github_labels.main)
    executor(github_templates.main)
    executor(github_workflows.main, args.no_docs, args.no_cd)
    if not args.no_gitpod:
        executor(gitpod.main)
    executor(nbstripout.main)
    executor(prettier.main, args.no_prettierrc)
    if is_python_repo:
        executor(black.main)
        executor(flake8.main)
        if not args.no_cd:
            executor(github_workflows.create_continuous_deployment)
        if args.pin_requirements != "no":
            executor(
                update_pip_constraints.main,
                cron_frequency=args.pin_requirements,
            )
        executor(pyupgrade.main)
        executor(release_drafter.main)
        executor(setup_cfg.main, args.ignore_author)
        executor(tox.main)
    if executor.error_messages:
        print(executor.merge_messages())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
