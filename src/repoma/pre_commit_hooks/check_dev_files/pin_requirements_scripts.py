"""Check if there is a ``pin_requirements.py`` script."""

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from repoma._utilities import (
    CONFIG_PATH,
    get_supported_python_versions,
    write_script,
)
from repoma.pre_commit_hooks.errors import PrecommitError


def check_constraints_folder() -> None:
    update_pin_requirements_script()
    remove_bash_script()
    update_github_workflows()


def update_pin_requirements_script() -> None:
    script_name = "pin_requirements.py"
    expected_script_path = CONFIG_PATH.repoma_src / "devtools" / script_name
    with open(expected_script_path) as stream:
        expected_script = stream.read()
    script_path = CONFIG_PATH.pip_constraints / script_name
    if not script_path.exists():
        write_script(content=expected_script, path=script_path)
        raise PrecommitError(
            f'This repository does not contain a "{script_name}" script.'
            " Problem has been fixed"
        )
    with open(script_path) as stream:
        existing_script = stream.read()
    if existing_script != expected_script:
        write_script(content=expected_script, path=script_path)
        raise PrecommitError(f'Updated "{script_name}" script')


def remove_bash_script() -> None:
    bash_script_name = CONFIG_PATH.pip_constraints / "upgrade.sh"
    if bash_script_name.exists():
        bash_script_name.unlink()
        raise PrecommitError(f'Removed deprecated "{bash_script_name}" script')


def update_github_workflows() -> None:
    def upgrade_workflow(workflow_file: str) -> None:
        expected_workflow_path = (
            CONFIG_PATH.repoma_src / "workflows" / workflow_file
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
        workflow_path = CONFIG_PATH.github_workflow_dir / workflow_file
        if not workflow_path.exists():
            yaml.dump(expected_data, workflow_path)
            raise PrecommitError(f'Created "{workflow_path}" workflow')
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            yaml.dump(expected_data, workflow_path)
            raise PrecommitError(f'Updated "{workflow_path}" workflow')

    upgrade_workflow("requirements-cron.yml")
    upgrade_workflow("requirements-pr.yml")
