"""Remove :file:`dependabot.yml` file, or update it if requested."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.check_dev_files.upgrade_lock import Frequency


def main(frequency: Frequency) -> None:
    def dump_dependabot_config() -> None:
        yaml.dump(expected, dependabot_path)
        msg = f"Updated {dependabot_path}"
        raise PrecommitError(msg)

    def append_ecosystem(ecosystem_name: str) -> None:
        new_ecosystem = deepcopy(github_actions_ecosystem)  # avoid YAML anchors
        new_ecosystem["package-ecosystem"] = ecosystem_name
        package_ecosystems.append(new_ecosystem)

    dependabot_path = CONFIG_PATH.github_workflow_dir.parent / "dependabot.yml"
    template_path = COMPWA_POLICY_DIR / dependabot_path
    yaml = create_prettier_round_trip_yaml()

    expected = yaml.load(template_path)
    if frequency not in {"no", "outsource"}:
        expected["multi-ecosystem-groups"]["lock"]["schedule"]["interval"] = frequency
    package_ecosystems = cast("list[dict[str, Any]]", expected["updates"])
    github_actions_ecosystem = package_ecosystems[0]
    if not is_committed(f"{CONFIG_PATH.github_workflow_dir / '*.yml'}"):
        package_ecosystems.pop(0)
    if is_committed("**/Manifest.toml"):
        append_ecosystem("julia")
    if is_committed("uv.lock"):
        append_ecosystem("uv")

    if not package_ecosystems:
        dependabot_path.unlink(missing_ok=True)
        msg = f"Removed {dependabot_path}"
        raise PrecommitError(msg)
        return
    if not dependabot_path.exists():
        dump_dependabot_config()
    existing = yaml.load(dependabot_path)
    if existing != expected:
        dump_dependabot_config()
