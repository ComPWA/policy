"""Update workflows that update pip constraints files.

See Also:
- https://github.com/ComPWA/update-pip-constraints
- https://github.com/ComPWA/update-pre-commit
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from compwa_policy.errors import PolicyError
from compwa_policy.github.dependabot import get_dependabot_ecosystems
from compwa_policy.github.workflows import remove_workflow, update_workflow
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.match import filter_patterns
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.session import Changelog, Session

Frequency = Literal[
    "monthly",
    "quarterly",
    "semiannually",
]
"""The frequency of updating lock files."""
__CRON_SCHEDULES: dict[Frequency, str] = {
    "monthly": "0 3 7 */1 *",
    "quarterly": "0 3 7 */3 *",
    "semiannually": "0 3 7 */6 *",
}
__TRIGGER_ECOSYSTEMS = {"julia", "pre-commit", "uv"}


def main(session: Session, frequency: Frequency, keep_workflow: set[str]) -> None:
    precommit = session.precommit
    _update_precommit_schedule(precommit, frequency)
    session.changelog += _remove_script("pin_requirements.py")
    session.changelog += _remove_script("upgrade.sh")
    _update_lock_workflow(session, frequency, keep_workflow)


def _remove_script(script_name: str) -> Changelog:
    bash_script_name = CONFIG_PATH.pip_constraints / script_name
    if bash_script_name.exists():
        bash_script_name.unlink()
        msg = f'Removed deprecated "{bash_script_name}" script'
        return [msg]
    return []


def _update_lock_workflow(
    session: Session, /, frequency: Frequency, keep_workflow: set[str]
) -> None:
    precommit = session.precommit

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
            get_dependabot_ecosystems() & __TRIGGER_ECOSYSTEMS
            or "autoupdate_schedule" in precommit.document.get("ci", {})
        ):
            del expected_data["on"]["schedule"]
        else:
            expected_data["on"]["schedule"][0]["cron"] = _to_cron_schedule(frequency)
        workflow_path = CONFIG_PATH.github_workflow_dir / workflow_file
        if not workflow_path.exists():
            session.changelog += update_workflow(yaml, expected_data, workflow_path)
            return
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            session.changelog += update_workflow(yaml, expected_data, workflow_path)

    if "lock.yml" not in keep_workflow:
        overwrite_workflow("lock.yml")
    for workflow in (
        "requirements.yml",
        "requirements-cron.yml",
        "requirements-pr.yml",
    ):
        if workflow not in keep_workflow:
            session.changelog += remove_workflow(workflow)


def _to_cron_schedule(frequency: Frequency) -> str:
    if frequency not in __CRON_SCHEDULES:
        msg = f'No cron schedule defined for frequency "{frequency}"'
        raise PolicyError(msg)
    return __CRON_SCHEDULES[frequency]


def _update_precommit_schedule(
    precommit: ModifiablePrecommit, frequency: Frequency
) -> None:
    ci_section = precommit.document.get("ci")
    if ci_section is None:
        return
    key = "autoupdate_schedule"
    if get_dependabot_ecosystems() & __TRIGGER_ECOSYSTEMS:
        frequency = "quarterly"
        if ci_section.get(key) == frequency:
            return
        ci_section[key] = "quarterly"
        precommit.changelog.append(
            "Set pre-commit autoupdate schedule to quarterly (maximum), because the"
            " schedule is now determined by Dependabot"
        )
    else:
        if frequency == "semiannually":
            frequency = "quarterly"
        if ci_section[key] != frequency:
            ci_section[key] = frequency
            precommit.changelog.append(
                f"Set pre-commit autoupdate schedule to {frequency!r}"
            )
