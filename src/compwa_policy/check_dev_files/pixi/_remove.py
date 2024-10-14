from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, remove_lines, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from pathlib import Path


def remove_pixi_configuration() -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(remove_lines, CONFIG_PATH.gitattributes, "pixi")
        do(_remove_file, CONFIG_PATH.pixi_lock)
        do(_remove_file, CONFIG_PATH.pixi_toml)
        do(
            vscode.remove_settings,
            {"files.associations": ["**/pixi.lock", "pixi.lock"]},
        )
        if not pyproject.has_table("tool.pixi"):
            return
        del pyproject._document["tool"]["pixi"]  # pyright: ignore[reportTypedDictNotRequiredAccess] # noqa: SLF001
        pyproject.changelog.append("Removed Pixi configuration table")


def _remove_file(path: Path) -> None:
    if not path.exists():
        return
    path.unlink(missing_ok=True)
    msg = f"Removed redundant file {path!r}"
    raise PermissionError(msg)
