from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, remove_lines, vscode
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from pathlib import Path


def remove_pixi_configuration() -> list[str]:
    changes = remove_lines(CONFIG_PATH.gitattributes, "pixi")
    changes += remove_lines(CONFIG_PATH.gitignore, ".*pixi.*")
    changes += _remove_file(CONFIG_PATH.pixi_lock)
    changes += _remove_file(CONFIG_PATH.pixi_toml)
    changes += vscode.remove_settings({
        "files.associations": ["**/pixi.lock", "pixi.lock"]
    })
    if CONFIG_PATH.pyproject.exists():
        with ModifiablePyproject.load() as pyproject:
            if not pyproject.has_table("tool.pixi"):
                return changes
            del pyproject._document["tool"]["pixi"]  # noqa: SLF001
            pyproject.changelog.append("Removed Pixi configuration table")
        changes += list(pyproject.changelog)
    return changes


def _remove_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    path.unlink(missing_ok=True)
    return [f"Removed redundant file {path!r}"]
