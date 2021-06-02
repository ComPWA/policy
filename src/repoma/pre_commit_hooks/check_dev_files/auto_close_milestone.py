# cspell:ignore mhutchie
"""Add a GitHub Action that auto-closes milestones on a new release.

See `github.com/mhutchie/update-milestone-on-release
<https://github.com/mhutchie/update-milestone-on-release>`_.
"""


import os

from repoma.pre_commit_hooks.errors import PrecommitError

__THIS_MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


def check_workflow_file() -> None:
    github_workflow_dir = ".github/workflows"
    workflow_file = "milestone.yml"
    expected_workflow_path = os.path.abspath(
        f"{__THIS_MODULE_DIR}/../../workflows/{workflow_file}"
    )
    with open(expected_workflow_path) as stream:
        expected_content = stream.read()
    workflow_path = f"{github_workflow_dir}/{workflow_file}"
    if not os.path.exists(workflow_path):
        write_script(expected_content, path=workflow_path)
        raise PrecommitError(f'Created "{workflow_path}" workflow')

    with open(workflow_path) as stream:
        existing_content = stream.read()
    if existing_content != expected_content:
        write_script(expected_content, path=workflow_path)
        raise PrecommitError(f'Updated "{workflow_path}" workflow')


def write_script(content: str, path: str) -> None:
    with open(path, "w") as stream:
        stream.write(content)
