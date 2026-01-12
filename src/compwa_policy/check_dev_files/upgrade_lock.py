"""Update workflows that update pip constraints files.

See Also:
- https://github.com/ComPWA/update-pip-constraints
- https://github.com/ComPWA/update-pre-commit
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from compwa_policy.check_dev_files.dependabot import get_dependabot_ecosystems
from compwa_policy.check_dev_files.github_workflows import (
    remove_workflow,
    update_workflow,
)
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import filter_patterns
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit

Frequency = Literal[
    "no",
    "monthly",
    "quarterly",
    "semiannually",
    "outsource",
]
"""The frequency of updating lock files."""
__CRON_SCHEDULES: dict[Frequency, str] = {
    "monthly": "0 3 7 */1 *",
    "quarterly": "0 3 7 */3 *",
    "semiannually": "0 3 7 */6 *",
}
__TRIGGER_ECOSYSTEMS = {"julia", "uv"}


def main(precommit: ModifiablePrecommit, frequency: Frequency) -> None:
    with Executor() as do:
        do(_update_precommit_schedule, precommit, frequency)
        do(_remove_script, "pin_requirements.py")
        do(_remove_script, "upgrade.sh")
        do(_update_requirement_workflow, frequency)


def _remove_script(script_name: str) -> None:
    bash_script_name = CONFIG_PATH.pip_constraints / script_name
    if bash_script_name.exists():
        bash_script_name.unlink()
        msg = f'Removed deprecated "{bash_script_name}" script'
        raise PrecommitError(msg)


def _update_requirement_workflow(frequency: Frequency) -> None:
    def overwrite_workflow(workflow_file: str) -> None:
        expected_workflow_path = (
            COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / workflow_file
        )
        yaml = create_prettier_round_trip_yaml()
        expected_data = yaml.load(expected_workflow_path)
        original_paths = expected_data["on"]["pull_request"]["paths"]
        existing_paths = filter_patterns(original_paths)
        if not existing_paths:
            msg = (
                "No paths defined for pull_request trigger. Expecting any of "
                + ", ".join(original_paths)
            )
            raise ValueError(msg)
        expected_data["on"]["pull_request"]["paths"] = existing_paths
        if (
            frequency == "outsource"
            or get_dependabot_ecosystems() & __TRIGGER_ECOSYSTEMS
        ):
            del expected_data["on"]["schedule"]
        else:
            expected_data["on"]["schedule"][0]["cron"] = _to_cron_schedule(frequency)
        workflow_path = CONFIG_PATH.github_workflow_dir / workflow_file
        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    with Executor() as do:
        do(overwrite_workflow, "lock.yml")
        do(remove_workflow, "requirements.yml")
        do(remove_workflow, "requirements-cron.yml")
        do(remove_workflow, "requirements-pr.yml")


def _to_cron_schedule(frequency: Frequency) -> str:
    if frequency not in __CRON_SCHEDULES:
        msg = f'No cron schedule defined for frequency "{frequency}"'
        raise PrecommitError(msg)
    return __CRON_SCHEDULES[frequency]


def _update_precommit_schedule(
    precommit: ModifiablePrecommit, frequency: Frequency
) -> None:
    ci_section = precommit.document.get("ci")
    if ci_section is None:
        return
    key = "autoupdate_schedule"
    if key not in ci_section:
        return
    if get_dependabot_ecosystems() & __TRIGGER_ECOSYSTEMS:
        del ci_section[key]
        precommit.changelog.append(
            "Deactivated pre-commit autoupdate schedule, because it is already"
            f" triggered by the {CONFIG_PATH.github_workflow_dir / 'lock.yml'}."
        )
    else:
        if frequency in {"outsource", "semiannually"}:
            frequency = "quarterly"
        if ci_section[key] != frequency:
            ci_section[key] = frequency
            precommit.changelog.append(
                f"Set pre-commit autoupdate schedule to {frequency!r}"
            )
