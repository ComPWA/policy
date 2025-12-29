"""Configuration of the :code:`ty` type checker."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from sphinx import TYPE_CHECKING

from compwa_policy.utilities import vscode
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit

TypeChecker = Literal["mypy", "pyright", "ty"]


def main(active: bool, precommit: ModifiablePrecommit) -> None:
    with ModifiablePyproject.load() as pyproject:
        if active:
            _update_vscode_settings(active)
        else:
            _remove_ty(precommit, pyproject)


def _update_vscode_settings(active: bool) -> None:
    settings = {
        "ty.completions.autoImport": False,
        "ty.diagnosticMode": "workspace",
        "ty.importStrategy": "fromEnvironment",
    }
    if active:
        vscode.update_settings(settings)
    else:
        vscode.remove_settings(settings)


def _remove_ty(precommit: ModifiablePrecommit, pyproject: ModifiablePyproject) -> None:
    config_path = Path("ty.toml")
    if config_path.exists():
        config_path.unlink()
        pyproject.changelog.append(f"Removed {config_path}")
    if pyproject.has_table("tool.ty"):
        del pyproject._document["tool"]["ty"]  # noqa: SLF001
        pyproject.changelog.append("Removed ty configuration table")
    pyproject.remove_dependency("ty")
    precommit.remove_hook("ty")
