from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, remove_configs, remove_lines, vscode

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Changelog, Session


def remove_pixi_configuration(session: Session, /) -> Changelog:
    changes = remove_lines(session, CONFIG_PATH.gitattributes, "pixi")
    changes += remove_lines(session, CONFIG_PATH.gitignore, ".*pixi.*")
    changes += remove_configs(
        session,
        [str(CONFIG_PATH.pixi_lock), str(CONFIG_PATH.pixi_toml)],
    )
    changes += vscode.remove_settings(
        session, {"files.associations": ["**/pixi.lock", "pixi.lock"]}
    )
    if CONFIG_PATH.pyproject.exists():
        pyproject = session.pyproject
    else:
        return changes
    if pyproject is None:
        return changes
    if pyproject.has_table("tool.pixi"):
        del pyproject._document["tool"]["pixi"]  # noqa: SLF001
        pyproject.changelog.append("Removed Pixi configuration table")
    return changes
