from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from pathlib import Path


def remove_pixi_configuration() -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_remove_pixi_configuration, pyproject)
        do(
            vscode.remove_settings,
            {"files.associations": ["**/pixi.lock", "pixi.lock"]},
        )


def _remove_pixi_configuration(pyproject: ModifiablePyproject) -> None:
    updated = False
    updated |= _remove_from_git_attributes("pixi")
    updated |= __remove(CONFIG_PATH.pixi_lock)
    updated |= __remove(CONFIG_PATH.pixi_toml)
    if pyproject.has_table("tool.pixi"):
        del pyproject._document["tool"]["pixi"]  # pyright: ignore[reportTypedDictNotRequiredAccess] # noqa: SLF001
        updated = True
    if updated:
        msg = "Removed Pixi configuration files"
        pyproject.changelog.append(msg)


def _remove_from_git_attributes(word: str) -> bool:
    if not CONFIG_PATH.gitattributes.exists():
        return False
    with open(CONFIG_PATH.gitattributes) as stream:
        lines = stream.readlines()
    filtered_lines = [line for line in lines if word not in line.lower()]
    if not any(line.strip() for line in filtered_lines):
        CONFIG_PATH.gitattributes.unlink()
        return True
    if len(filtered_lines) == len(lines):
        return False
    with open(CONFIG_PATH.gitattributes, "w") as stream:
        stream.writelines(filtered_lines)
    return True


def __remove(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink(missing_ok=True)
    return True
