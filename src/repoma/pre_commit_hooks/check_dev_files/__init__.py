"""A collection of scripts that check the file structure of a repository."""

import argparse
import sys
from typing import Optional, Sequence

from ._executor import Executor
from .black import check_black_config
from .check_labels import check_has_labels
from .cspell_config import fix_cspell_config
from .editor_config_hook import check_editor_config_hook
from .flake8 import check_flake8_config
from .github_templates import check_github_templates
from .github_workflows import check_docs_workflow, check_milestone_workflow
from .gitpod import check_gitpod_config
from .nbstripout import check_nbstripout
from .pin_requirements_scripts import check_constraints_folder
from .prettier_config import fix_prettier_config
from .pyupgrade import update_pyupgrade_hook
from .setup_cfg import fix_setup_cfg
from .tox_config import check_tox_ini


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
        "--no-prettierrc",
        default=False,
        action="store_true",
        help=(
            "Remove the prettierrc, so that Prettier's default values are"
            " used."
        ),
    )
    parser.add_argument(
        "--allow-labels",
        default=False,
        action="store_true",
        help="Do not perform the check on labels.toml",
    )
    parser.add_argument(
        "--pin-requirements",
        default=False,
        action="store_true",
        help="Add a script to pin developer requirements to a constraint file",
    )
    args = parser.parse_args(argv)
    is_python_repo = not args.no_python

    executor = Executor()
    executor(check_milestone_workflow)
    executor(check_docs_workflow)
    executor(check_editor_config_hook)
    if not args.allow_labels:
        executor(check_has_labels)
    executor(fix_cspell_config)
    executor(fix_prettier_config, args.no_prettierrc)
    executor(check_black_config)
    executor(check_flake8_config)
    executor(check_github_templates)
    executor(check_gitpod_config)
    executor(check_nbstripout)
    executor(update_pyupgrade_hook)
    if is_python_repo:
        if args.pin_requirements:
            executor(check_constraints_folder)
        executor(fix_setup_cfg, args.ignore_author)
        executor(check_tox_ini)
    if executor.error_messages:
        print("\n---------------\n\n".join(executor.error_messages))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
