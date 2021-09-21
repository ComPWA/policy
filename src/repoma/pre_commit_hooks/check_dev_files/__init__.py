"""A collection of scripts that check the file structure of a repository."""

import argparse
import sys
from typing import Optional, Sequence

from repoma.pre_commit_hooks.errors import PrecommitError

from . import auto_close_milestone
from .check_labels import check_has_labels
from .cspell_config import fix_cspell_config
from .editor_config_hook import check_editor_config_hook
from .github_templates import check_github_templates
from .gitpod import check_gitpod_config
from .pin_requirements_scripts import check_constraints_folder
from .prettier_config import fix_prettier_config
from .tox_config import check_tox_ini


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--no-python",
        default=False,
        action="store_true",
        help="Skip check that concern config files for Python projects.",
    )
    parser.add_argument(
        "--no-fix",
        default=False,
        action="store_true",
        help="Fix the identified problems.",
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
        "--pin-requirements",
        default=False,
        action="store_true",
        help="Add a script to pin developer requirements to a constraint file",
    )
    args = parser.parse_args(argv)
    fix = not args.no_fix
    is_python_repo = not args.no_python
    try:
        auto_close_milestone.check_workflow_file()
        check_editor_config_hook()
        if not args.allow_labels:
            check_has_labels(fix)
        fix_cspell_config()
        fix_prettier_config(args.no_prettierrc)
        check_github_templates()
        check_gitpod_config()
        if is_python_repo:
            if args.pin_requirements:
                check_constraints_folder()
            check_tox_ini(fix)
        return 0
    except PrecommitError as exception:
        print(str("\n".join(exception.args)))
        return 1


if __name__ == "__main__":
    sys.exit(main())
