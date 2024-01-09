"""Update workflows that update pip constraints files.

See Also:
- https://github.com/ComPWA/update-pip-constraints
- https://github.com/ComPWA/update-pre-commit
"""

from __future__ import annotations

import sys

from repoma.check_dev_files.github_workflows import remove_workflow, update_workflow
from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import load_round_trip_precommit_config
from repoma.utilities.yaml import create_prettier_round_trip_yaml

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


Frequency = Literal[
    "no",
    "biweekly",
    "monthly",
    "bimonthly",
    "quarterly",
    "biannually",
    "outsource",
]
__CRON_SCHEDULES: dict[Frequency, str] = {
    "biweekly": "0 2 * * 1",
    "monthly": "0 3 7 */1 *",
    "bimonthly": "0 3 7 */2 *",
    "quarterly": "0 3 7 */3 *",
    "biannually": "0 3 7 */6 *",
}


def main(frequency: Frequency) -> None:
    executor = Executor()
    if frequency == "outsource":
        executor(_check_precommit_schedule)
    executor(_remove_script, "pin_requirements.py")
    executor(_remove_script, "upgrade.sh")
    executor(_update_requirement_workflow, frequency)
    executor.finalize()


def _remove_script(script_name: str) -> None:
    bash_script_name = CONFIG_PATH.pip_constraints / script_name
    if bash_script_name.exists():
        bash_script_name.unlink()
        msg = f'Removed deprecated "{bash_script_name}" script'
        raise PrecommitError(msg)


def _update_requirement_workflow(frequency: Frequency) -> None:
    def overwrite_workflow(workflow_file: str) -> None:
        expected_workflow_path = (
            REPOMA_DIR / CONFIG_PATH.github_workflow_dir / workflow_file
        )
        yaml = create_prettier_round_trip_yaml()
        expected_data = yaml.load(expected_workflow_path)
        if frequency == "outsource":
            del expected_data["on"]["schedule"]
        else:
            expected_data["on"]["schedule"][0]["cron"] = _to_cron_schedule(frequency)
        workflow_path = CONFIG_PATH.github_workflow_dir / workflow_file
        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    executor = Executor()
    executor(overwrite_workflow, "requirements.yml")
    executor(remove_workflow, "requirements-cron.yml")
    executor(remove_workflow, "requirements-pr.yml")
    executor.finalize()


def _to_cron_schedule(frequency: Frequency) -> str:
    if frequency not in __CRON_SCHEDULES:
        msg = f'No cron schedule defined for frequency "{frequency}"'
        raise PrecommitError(msg)
    return __CRON_SCHEDULES[frequency]


def _check_precommit_schedule() -> None:
    msg = (
        "Cannot outsource pip constraints updates, because autoupdate_schedule has not"
        f" been set under the ci key in {CONFIG_PATH.precommit}. See"
        " https://pre-commit.ci/#configuration-autoupdate_schedule."
    )
    if not CONFIG_PATH.precommit.exists():
        raise PrecommitError(msg)
    config, _ = load_round_trip_precommit_config()
    schedule = config.get("ci", {}).get("autoupdate_schedule")
    if schedule is None:
        raise PrecommitError(msg)
