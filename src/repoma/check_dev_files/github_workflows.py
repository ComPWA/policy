"""Check :file:`.github/workflows` folder content."""

import os
import re

from repoma._utilities import CONFIG_PATH, REPOMA_DIR, write_script
from repoma.errors import PrecommitError


def main() -> None:
    check_milestone_workflow()
    check_docs_workflow()


def check_milestone_workflow() -> None:
    """Add a GitHub Action that auto-closes milestones on a new release.

    See `github.com/mhutchie/update-milestone-on-release
    <https://github.com/mhutchie/update-milestone-on-release>`_.
    """
    # cspell:ignore mhutchie
    _copy_workflow_file("milestone.yml")


def check_docs_workflow() -> None:
    if os.path.exists("./docs/") or os.path.exists("./doc/"):
        _copy_workflow_file("ci-docs.yml")
        _copy_workflow_file("linkcheck.yml")


def _copy_workflow_file(filename: str) -> None:
    expected_workflow_path = (
        REPOMA_DIR / CONFIG_PATH.github_workflow_dir / filename
    )
    with open(expected_workflow_path) as stream:
        expected_content = stream.read()
    if not CONFIG_PATH.pip_constraints.exists():
        expected_content = _remove_constraint_pinning(expected_content)

    workflow_path = f"{CONFIG_PATH.github_workflow_dir}/{filename}"
    if not os.path.exists(workflow_path):
        write_script(expected_content, path=workflow_path)
        raise PrecommitError(f'Created "{workflow_path}" workflow')

    with open(workflow_path) as stream:
        existing_content = stream.read()
    if existing_content != expected_content:
        write_script(expected_content, path=workflow_path)
        raise PrecommitError(f'Updated "{workflow_path}" workflow')


def _remove_constraint_pinning(content: str) -> str:
    """Remove constraint flags from a pip install statement.

    >>> src = "pip install -c .constraints/py3.7.txt .[dev]"
    >>> _remove_constraint_pinning(src)
    'pip install .[dev]'
    """
    return re.sub(
        pattern=fr"-c {CONFIG_PATH.pip_constraints}/py3\.\d\.txt\s*",
        repl="",
        string=content,
    )
