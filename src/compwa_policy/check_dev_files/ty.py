"""Configuration of the :code:`ty` type checker."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ruamel.yaml.comments import CommentedSeq

from compwa_policy.utilities import vscode
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.readme import add_badge, remove_badge

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit

TypeChecker = Literal["mypy", "pyright", "ty"]
"""The type of type checkers supported."""


def main(
    type_checkers: set[TypeChecker],
    keep_precommit: bool,
    precommit: ModifiablePrecommit,
) -> None:
    with ModifiablePyproject.load() as pyproject:
        _update_vscode_settings(type_checkers)
        if "ty" in type_checkers:
            _update_configuration(pyproject)
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
            vscode.remove_settings(["python.languageServer"])
        vscode.add_extension_recommendation("astral-sh.ty")
        vscode.update_settings(settings)
        add_badge(
            "[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)"
        )
    else:
        vscode.remove_extension_recommendation("astral-sh.ty", unwanted=True)
        vscode.remove_settings([*settings, "python.languageServer"])


def _update_configuration(pyproject: ModifiablePyproject) -> None:
    def _remove_rule(key: str, default: Literal["error", "ignore", "warn"]) -> None:
        if ty_config.get(key) == default:
            del ty_config[key]
            pyproject.changelog.append(f"Removed tool.ty.rules.{key}")

    def _update_rule(key: str, value: Literal["error", "ignore", "warn"]) -> None:
        if key not in ty_config:
            ty_config[key] = value
            pyproject.changelog.append(f'Set tool.ty.rules.{key} = "{value}"')

    ty_config = pyproject.get_table("tool.ty.rules", create=True)
    _remove_rule("unused-ignore-comment", "warn")
    _update_rule("division-by-zero", "warn")
    _update_rule("possibly-missing-import", "warn")
    _update_rule("possibly-unresolved-reference", "warn")


def _update_precommit_config(precommit: ModifiablePrecommit) -> None:
    args = CommentedSeq(["--no-progress", "--output-format=concise"])
    args.fa.set_flow_style()
    types_or = CommentedSeq(["python", "pyi", "jupyter"])
    types_or.fa.set_flow_style()
    hook = Hook(
        id="ty",
        name="ty",
        entry="ty check",
        args=args,
        pass_filenames=False,
        require_serial=True,
        language="system",
        types_or=types_or,
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
    remove_badge(r".*https://.+\.com/astral\-sh/ty/main/assets/badge/v0\.json.*")
