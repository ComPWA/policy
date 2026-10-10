"""Remove :file:`dependabot.yml` file, or update it if requested."""

from __future__ import annotations

from copy import deepcopy
from functools import cache
from typing import TYPE_CHECKING, Any, cast

import yaml

from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.config import DependabotEcosystem
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Changelog, Session


@check_hook(
    group="github",
    paths=[CONFIG_PATH.precommit, "uv.lock"],
    directories=(CONFIG_PATH.github_workflow_dir.parent,),
    patterns=("(.*/)?Manifest\\.toml",),
)
def check(session: Session, args: Arguments, _: CheckContext) -> None:
    frequency = args.upgrade_frequency

    def dump_dependabot_config() -> Changelog:
        dependabot_path.parent.mkdir(exist_ok=True)
        rt_yaml.dump(expected, dependabot_path)
        return [f"Updated {dependabot_path}"]

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
    ecosystems = args.dependabot_ecosystems
    if ecosystems is None:
        ecosystems = _detect_ecosystems()
    package_ecosystems = [get_ecosystem(name) for name in sorted(ecosystems)]

    if not package_ecosystems:
        if dependabot_path.exists():
            dependabot_path.unlink()
            session.changelog.append(f"Removed {dependabot_path}")
        return
    expected["updates"] = package_ecosystems
    if not dependabot_path.exists():
        session.changelog += dump_dependabot_config()
        return
    existing = rt_yaml.load(dependabot_path)
    if existing != expected:
        session.changelog += dump_dependabot_config()


def _detect_ecosystems() -> set[DependabotEcosystem]:
    ecosystems: set[DependabotEcosystem] = set()
    if is_committed(f"{CONFIG_PATH.github_workflow_dir / '*.yml'}", untracked=True):
        ecosystems.add("github-actions")
    if is_committed("**/Manifest.toml", untracked=True):
        ecosystems.add("julia")
    if is_committed(".pre-commit-config.yaml", untracked=True):
        ecosystems.add("pre-commit")
    if is_committed("uv.lock", untracked=True):
        ecosystems.add("uv")
    return ecosystems


@cache
def get_dependabot_ecosystems() -> set[str]:
    dependabot_path = CONFIG_PATH.github_workflow_dir.parent / "dependabot.yml"
    if not dependabot_path.exists():
        return set()
    with dependabot_path.open("r") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    return {entry["package-ecosystem"] for entry in config["updates"]}
