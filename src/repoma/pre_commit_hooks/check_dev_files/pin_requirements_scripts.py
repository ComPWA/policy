"""Check if there is a ``pin_requirements.py`` script."""

import os
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from repoma._utilities import (
    CONFIG_PATH,
    get_supported_python_versions,
    write_script,
)
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
    def upgrade_workflow(workflow_file: str) -> None:
        expected_workflow_path = Path(
            os.path.abspath(
                f"{__THIS_MODULE_DIR}/../../workflows/{workflow_file}"
            )
        )
        yaml = YAML(typ="rt")
        yaml.preserve_quotes = True  # type: ignore[assignment]
        expected_data = yaml.load(expected_workflow_path)
        supported_python_versions = get_supported_python_versions()
        formatted_python_versions = list(
            map(DoubleQuotedScalarString, supported_python_versions)
        )
        jobs = list(expected_data["jobs"])
        first_job = jobs[0]
        expected_data["jobs"][first_job]["strategy"]["matrix"][
            "python-version"
        ] = formatted_python_versions
        workflow_path = Path(
            f"{CONFIG_PATH.github_workflow_dir}/{workflow_file}"
        )
        if not workflow_path.exists():
            yaml.dump(expected_data, workflow_path)
            raise PrecommitError(f'Created "{workflow_path}" workflow')
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            yaml.dump(expected_data, workflow_path)
            raise PrecommitError(f'Updated "{workflow_path}" workflow')

    upgrade_workflow("requirements-cron.yml")
    upgrade_workflow("requirements-pr.yml")
