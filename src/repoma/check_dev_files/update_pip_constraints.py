"""Update workflows that update pip constraints files.

See Also:
- https://github.com/ComPWA/update-pip-constraints
- https://github.com/ComPWA/update-pre-commit
"""

from repoma.check_dev_files.github_workflows import remove_workflow, update_workflow
from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR
from repoma.utilities.executor import Executor
from repoma.utilities.yaml import create_prettier_round_trip_yaml

__CRON_SCHEDULES = {
    "biweekly": "0 2 * * 1",
    "monthly": "0 3 7 */1 *",
    "bimonthly": "0 3 7 */2 *",
    "quarterly": "0 3 7 */3 *",
    "biannually": "0 3 7 */6 *",
}


def main(cron_frequency: str) -> None:
    executor = Executor()
    executor(_remove_script, "pin_requirements.py")
    executor(_remove_script, "upgrade.sh")
    executor(_update_requirement_workflow, cron_frequency)
    executor.finalize()


def _remove_script(script_name: str) -> None:
    bash_script_name = CONFIG_PATH.pip_constraints / script_name
    if bash_script_name.exists():
        bash_script_name.unlink()
        msg = f'Removed deprecated "{bash_script_name}" script'
        raise PrecommitError(msg)


def _update_requirement_workflow(frequency: str) -> None:
    def overwrite_workflow(workflow_file: str, cron_schedule: str) -> None:
        expected_workflow_path = (
            REPOMA_DIR / CONFIG_PATH.github_workflow_dir / workflow_file
        )
        yaml = create_prettier_round_trip_yaml()
        expected_data = yaml.load(expected_workflow_path)
        expected_data["on"]["schedule"][0]["cron"] = cron_schedule
        workflow_path = CONFIG_PATH.github_workflow_dir / workflow_file
        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    executor = Executor()
    executor(overwrite_workflow, "requirements.yml", _to_cron_schedule(frequency))
    executor(remove_workflow, "requirements-cron.yml")
    executor(remove_workflow, "requirements-pr.yml")
    executor.finalize()


def _to_cron_schedule(frequency: str) -> str:
    schedule = __CRON_SCHEDULES.get(frequency)
    if schedule is None:
        msg = f'No cron schedule defined for frequency "{frequency}"'
        raise PrecommitError(msg)
    return schedule
