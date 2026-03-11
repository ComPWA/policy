"""Remove :file:`dependabot.yml` file, or update it if requested."""

from __future__ import annotations

from copy import deepcopy
from functools import cache
from typing import TYPE_CHECKING, Any, cast

import yaml

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.check_dev_files.upgrade_lock import Frequency


def main(frequency: Frequency) -> None:  # noqa: C901
    def dump_dependabot_config() -> None:
        dependabot_path.parent.mkdir(exist_ok=True)
        rt_yaml.dump(expected, dependabot_path)
        msg = f"Updated {dependabot_path}"
        raise PrecommitError(msg)

    def get_ecosystem(ecosystem_name: str, /) -> dict[str, Any]:
        new_ecosystem = deepcopy(template_ecosystem)  # avoid YAML anchors
        new_ecosystem["package-ecosystem"] = ecosystem_name
        return new_ecosystem

    dependabot_path = CONFIG_PATH.github_workflow_dir.parent / "dependabot.yml"
    template_path = COMPWA_POLICY_DIR / dependabot_path
    rt_yaml = create_prettier_round_trip_yaml()

    expected = rt_yaml.load(template_path)
    if frequency is not None:
        expected["multi-ecosystem-groups"]["lock"]["schedule"]["interval"] = frequency
    template_ecosystem = cast("dict[str, Any]", expected["updates"][0])
    package_ecosystems: list[dict[str, Any]] = []
    if is_committed(f"{CONFIG_PATH.github_workflow_dir / '*.yml'}"):
        package_ecosystems.append(get_ecosystem("github-actions"))
    if is_committed("**/Manifest.toml"):
        package_ecosystems.append(get_ecosystem("julia"))
    if is_committed(".pre-commit-config.yaml"):
        package_ecosystems.append(get_ecosystem("pre-commit"))
    if is_committed("uv.lock"):
        package_ecosystems.append(get_ecosystem("uv"))

    if not package_ecosystems:
        dependabot_path.unlink(missing_ok=True)
        msg = f"Removed {dependabot_path}"
        raise PrecommitError(msg)
        return
    expected["updates"] = package_ecosystems
    if not dependabot_path.exists():
        dump_dependabot_config()
    existing = rt_yaml.load(dependabot_path)
    if existing != expected:
        dump_dependabot_config()


@cache
def get_dependabot_ecosystems() -> set[str]:
    dependabot_path = CONFIG_PATH.github_workflow_dir.parent / "dependabot.yml"
    if not dependabot_path.exists():
        return set()
    with dependabot_path.open("r") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    return {entry["package-ecosystem"] for entry in config["updates"]}
