from __future__ import annotations

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.match import git_ls_files
from compwa_policy.utilities.pyproject import Pyproject


def has_pixi_config(pyproject: Pyproject | None = None) -> bool:
    if git_ls_files("pixi.lock", "pixi.toml"):
        return True
    if pyproject is not None:
        return pyproject.has_table("tool.pixi")
    return CONFIG_PATH.pyproject.exists() and Pyproject.load().has_table("tool.pixi")
