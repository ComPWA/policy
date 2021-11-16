"""Update workflows that update pip constraints files.

See Also:
- https://github.com/ComPWA/update-pip-constraints
- https://github.com/ComPWA/update-pre-commit
"""

from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR
from repoma.utilities.executor import Executor
from repoma.utilities.setup_cfg import get_supported_python_versions
from repoma.utilities.yaml import create_prettier_round_trip_yaml


def main() -> None:
    executor = Executor()
    executor(_remove_script, "pin_requirements.py")
    executor(_remove_script, "upgrade.sh")
    executor(_update_github_workflows)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _remove_script(script_name: str) -> None:
    bash_script_name = CONFIG_PATH.pip_constraints / script_name
    if bash_script_name.exists():
        bash_script_name.unlink()
        raise PrecommitError(f'Removed deprecated "{bash_script_name}" script')


def _update_github_workflows() -> None:
    def overwrite_workflow(workflow_file: str) -> None:
        expected_workflow_path = (
            REPOMA_DIR / CONFIG_PATH.github_workflow_dir / workflow_file
        )
        yaml = create_prettier_round_trip_yaml()
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

    executor = Executor()
    executor(overwrite_workflow, "requirements-cron.yml")
    executor(overwrite_workflow, "requirements-pr.yml")
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())
