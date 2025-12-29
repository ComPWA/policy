"""Configuration of the :code:`ty` type checker."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ruamel.yaml.comments import CommentedSeq

from compwa_policy.utilities import vscode
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit

TypeChecker = Literal["mypy", "pyright", "ty"]


def main(
    type_checkers: set[TypeChecker],
    keep_precommit: bool,
    precommit: ModifiablePrecommit,
) -> None:
    with ModifiablePyproject.load() as pyproject:
        _update_vscode_settings(type_checkers)
        if "ty" in type_checkers:
            pyproject.add_dependency("ty", dependency_group=["style", "dev"])
            if not keep_precommit:
                _update_precommit_config(precommit)
        else:
            _remove_ty(precommit, pyproject)


def _update_vscode_settings(type_checkers: set[TypeChecker]) -> None:
    settings = {
        "ty.completions.autoImport": False,
        "ty.diagnosticMode": "workspace",
        "ty.importStrategy": "fromEnvironment",
    }
    if "ty" in type_checkers:
        if "pyright" not in type_checkers:
            settings["python.languageServer"] = "None"
        vscode.update_settings(settings)
    else:
        vscode.remove_settings(settings)


def _update_precommit_config(precommit: ModifiablePrecommit) -> None:
    types_or = CommentedSeq(["python", "pyi", "jupyter"])
    types_or.fa.set_flow_style()
    hook = Hook(
        id="ty",
        name="ty",
        entry="ty",
        args=[
            "check",
            "--output-format=concise",
            "--respect-ignore-files",
        ],
        require_serial=True,
        language="system",
        types_or=types_or,  # ty:ignore[invalid-argument-type]
    )
    expected_repo = Repo(repo="local", hooks=[hook])
    precommit.update_single_hook_repo(expected_repo)


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
