from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, remove_configs, remove_lines, vscode
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Changelog


def remove_pixi_configuration(
    pyproject: ModifiablePyproject | None = None,
) -> Changelog:
    changes = remove_lines(CONFIG_PATH.gitattributes, "pixi")
    changes += remove_lines(CONFIG_PATH.gitignore, ".*pixi.*")
    changes += remove_configs([str(CONFIG_PATH.pixi_lock), str(CONFIG_PATH.pixi_toml)])
    changes += vscode.remove_settings({
        "files.associations": ["**/pixi.lock", "pixi.lock"]
    })
    if pyproject is None and CONFIG_PATH.pyproject.exists():
        with ModifiablePyproject.load() as config:
            remove_pixi_configuration(config)
            changes += list(config.changelog)
    elif pyproject is not None and pyproject.has_table("tool.pixi"):
        del pyproject._document["tool"]["pixi"]  # noqa: SLF001
        pyproject.changelog.append("Removed Pixi configuration table")
    return changes
