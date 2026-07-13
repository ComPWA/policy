from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, remove_configs, remove_lines, vscode

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Session


def remove_pixi_configuration(session: Session, /) -> None:
    remove_lines(session, CONFIG_PATH.gitattributes, "pixi")
    remove_lines(session, CONFIG_PATH.gitignore, ".*pixi.*")
    remove_configs(
        session,
        [str(CONFIG_PATH.pixi_lock), str(CONFIG_PATH.pixi_toml)],
    )
    vscode.remove_settings(
        session, {"files.associations": ["**/pixi.lock", "pixi.lock"]}
    )
    if CONFIG_PATH.pyproject.exists():
        pyproject = session.pyproject
    else:
        return
    if pyproject is None:
        return
    if pyproject.has_table("tool.pixi"):
        del pyproject._document["tool"]["pixi"]  # noqa: SLF001
        pyproject.changelog.append("Removed Pixi configuration table")
