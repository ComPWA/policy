"""Check :file:`.github/workflows` folder content."""

import os
import re

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, write
from repoma.utilities.executor import Executor


def main(no_docs: bool) -> None:
    executor = Executor()
    executor(check_milestone_workflow)
    if not no_docs:
        executor(check_docs_workflow)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def create_continuous_deployment() -> None:
    _copy_workflow_file("cd.yml")


def check_milestone_workflow() -> None:
    """Add a GitHub Action that auto-closes milestones on a new release.

    See `github.com/mhutchie/update-milestone-on-release
    <https://github.com/mhutchie/update-milestone-on-release>`_.
    """
    # cspell:ignore mhutchie
    _copy_workflow_file("milestone.yml")


def check_docs_workflow() -> None:
    if os.path.exists("./docs/") or os.path.exists("./doc/"):
        executor = Executor()
        executor(_copy_workflow_file, "ci-docs.yml")
        executor(_copy_workflow_file, "linkcheck.yml")
        if executor.error_messages:
            raise PrecommitError(executor.merge_messages())


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
        write(expected_content, target=workflow_path)
        raise PrecommitError(f'Created "{workflow_path}" workflow')

    with open(workflow_path) as stream:
        existing_content = stream.read()
    if existing_content != expected_content:
        write(expected_content, target=workflow_path)
        raise PrecommitError(f'Updated "{workflow_path}" workflow')


def _remove_constraint_pinning(content: str) -> str:
    """Remove constraint flags from a pip install statement.

    >>> src = "pip install -c .constraints/py3.7.txt .[dev]"
    >>> _remove_constraint_pinning(src)
    'pip install .[dev]'
    """
    return re.sub(
        pattern=rf"-c {CONFIG_PATH.pip_constraints}/py3\.\d\.txt\s*",
        repl="",
        string=content,
    )
