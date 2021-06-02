"""Check if there is a ``pin_requirements.py`` script."""

import os

from repoma.pre_commit_hooks.errors import PrecommitError

__CONSTRAINTS_DIR = ".constraints"
__SCRIPT_NAME = "pin_requirements.py"
__THIS_MODULE_DIR = os.path.abspath(os.path.dirname(__file__))
__EXPECTED_SCRIPT_PATH = os.path.abspath(
    f"{__THIS_MODULE_DIR}/../../devtools/{__SCRIPT_NAME}"
)


def check_constraints_folder() -> None:
    update_pin_requirements_script()
    remove_bash_script()
    update_github_workflows()


def update_pin_requirements_script() -> None:
    with open(__EXPECTED_SCRIPT_PATH) as stream:
        expected_script = stream.read()
    if not os.path.exists(f"{__CONSTRAINTS_DIR}/{__SCRIPT_NAME}"):
        write_script(
            content=expected_script,
            path=f"{__CONSTRAINTS_DIR}/{__SCRIPT_NAME}",
        )
        raise PrecommitError(
            f'This repository does not contain a "{__SCRIPT_NAME}" script.'
            " Problem has been fixed"
        )
    with open(f"{__CONSTRAINTS_DIR}/{__SCRIPT_NAME}") as stream:
        existing_script = stream.read()
    if existing_script != expected_script:
        write_script(
            content=expected_script,
            path=f"{__CONSTRAINTS_DIR}/{__SCRIPT_NAME}",
        )
        raise PrecommitError(f'Updated "{__SCRIPT_NAME}" script')


def remove_bash_script() -> None:
    bash_script_name = f"{__CONSTRAINTS_DIR}/upgrade.sh"
    if os.path.exists(bash_script_name):
        os.remove(bash_script_name)
        raise PrecommitError(f'Removed deprecated "{bash_script_name}" script')


def update_github_workflows() -> None:
    github_workflow_dir = ".github/workflows"

    def upgrade_workflow(workflow_file: str) -> None:
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

    upgrade_workflow("requirements-cron.yml")
    upgrade_workflow("requirements-pr.yml")


def write_script(content: str, path: str) -> None:
    with open(path, "w") as stream:
        stream.write(content)
