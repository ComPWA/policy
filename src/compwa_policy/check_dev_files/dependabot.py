"""Remove :file:`dependabot.yml` file, or update it if requested."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal, cast

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from pathlib import Path


DependabotOption = Literal["keep", "update"]
"""Allowed options for the :code:`--dependabot` argument."""


def main(allow_dependabot: DependabotOption | None) -> None:
    dependabot_path = CONFIG_PATH.github_workflow_dir.parent / "dependabot.yml"
    if allow_dependabot is None:
        _remove_dependabot(dependabot_path)
    elif allow_dependabot == "update":
        _update_dependabot(dependabot_path)


def _remove_dependabot(dependabot_path: Path) -> None:
    if not dependabot_path.exists():
        return
    dependabot_path.unlink()
    msg = (
        f"Removed {dependabot_path}, because it is GitHub workflows have been"
        " outsourced to https://github.com/ComPWA/actions"
    )
    raise PrecommitError(msg)


def _update_dependabot(dependabot_path: Path) -> None:
    def dump_dependabot_template() -> None:
        yaml.dump(expected_config, dependabot_path)
        msg = f"Updated {dependabot_path}"
        raise PrecommitError(msg)

    def append_ecosystem(ecosystem_name: str) -> None:
        new_ecosystem = deepcopy(github_actions_ecosystem)  # avoid YAML anchors
        new_ecosystem["package-ecosystem"] = ecosystem_name
        package_ecosystems.append(new_ecosystem)

    yaml = create_prettier_round_trip_yaml()
    template_path = COMPWA_POLICY_DIR / dependabot_path
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
