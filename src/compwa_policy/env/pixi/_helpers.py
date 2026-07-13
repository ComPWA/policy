from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities.match import git_ls_files

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Session


def has_pixi_config(session: Session, /) -> bool:
    if git_ls_files("pixi.lock", "pixi.toml"):
        return True
    pyproject = session.pyproject
    if pyproject is not None:
        return pyproject.has_table("tool.pixi")
    return False
