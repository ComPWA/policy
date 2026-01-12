"""Remove :file:`dependabot.yml` file, or update it if requested."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml


def main() -> None:
    def dump_dependabot_template() -> None:
        yaml.dump(expected_config, dependabot_path)
        msg = f"Updated {dependabot_path}"
        raise PrecommitError(msg)

    def append_ecosystem(ecosystem_name: str) -> None:
        new_ecosystem = deepcopy(github_actions_ecosystem)  # avoid YAML anchors
        new_ecosystem["package-ecosystem"] = ecosystem_name
        package_ecosystems.append(new_ecosystem)

    dependabot_path = CONFIG_PATH.github_workflow_dir.parent / "dependabot.yml"
    template_path = COMPWA_POLICY_DIR / dependabot_path
    yaml = create_prettier_round_trip_yaml()
    expected_config = yaml.load(template_path)
    package_ecosystems = cast("list[dict[str, Any]]", expected_config["updates"])
    github_actions_ecosystem = package_ecosystems[0]
    if is_committed("**/Manifest.toml"):
        append_ecosystem("julia")
    if is_committed("uv.lock"):
        append_ecosystem("uv")
    if not dependabot_path.exists():
        dump_dependabot_template()
    existing_config = yaml.load(dependabot_path)
    if existing_config != expected_config:
        dump_dependabot_template()
