"""Remove :file:`dependabot.yml` file, or update it if requested."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH

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
    template_path = COMPWA_POLICY_DIR / dependabot_path
    with open(template_path) as f:
        template = f.read()
    if not dependabot_path.exists():
        __dump_dependabot_template(template, dependabot_path)
    with open(dependabot_path) as f:
        dependabot = f.read()
    if dependabot != template:
        __dump_dependabot_template(template, dependabot_path)


def __dump_dependabot_template(content: str, path: Path) -> None:
    with open(path, "w") as f:
        f.write(content)
    msg = f"Updated {path}"
    raise PrecommitError(msg)
