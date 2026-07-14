"""Configuration of the :code:`ty` type checker."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.precommit.getters import find_hook
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.readme import add_badge, remove_badge
from compwa_policy.utilities.yaml import read_preserved_yaml

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.config import TypeChecker
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.pyproject import ModifiablePyproject
    from compwa_policy.utilities.session import Session


@check_hook(
    group="python",
    paths=[
        CONFIG_PATH.precommit,
        CONFIG_PATH.pyproject,
        CONFIG_PATH.readme,
        CONFIG_PATH.vscode_extensions,
        CONFIG_PATH.vscode_settings,
        "ty.toml",
    ],
    enabled=lambda _args, ctx: ctx.is_python_repo,
)
def check(session: Session, args: Arguments, _: CheckContext) -> None:
    _update_vscode_settings(session, args.type_checker)
    config = session.pyproject
    if config is None:
        return
    if "ty" in args.type_checker:
        _update_configuration(config)
        config.add_dependency("ty", dependency_group=["style", "dev"])
        _update_precommit_config(session)
        add_badge(
            session,
            "[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)",
        )
    else:
        _remove_ty(session)


def _update_vscode_settings(
    session: Session,
    /,
    type_checkers: set[TypeChecker],
) -> None:
    settings = {
        "ty.completions.autoImport": False,
        "ty.diagnosticMode": "workspace",
        "ty.importStrategy": "fromEnvironment",
    }
    if "ty" in type_checkers:
        if "pyright" not in type_checkers:
            vscode.remove_settings(session, ["python.languageServer"])
        vscode.add_extension_recommendation(session, "astral-sh.ty")
        vscode.update_settings(session, settings)
    else:
        vscode.remove_extension_recommendation(session, "astral-sh.ty", unwanted=True)
        vscode.remove_settings(session, [*settings, "python.languageServer"])


def _update_configuration(pyproject: ModifiablePyproject) -> None:
    def _remove_rule(key: str, default: Literal["error", "ignore", "warn"]) -> None:
        if ty_rules.get(key) == default:
            del ty_rules[key]
            pyproject.changelog.append(f"Removed tool.ty.rules.{key}")

    def _update_rule(key: str, value: Literal["error", "ignore", "warn"]) -> None:
        if key not in ty_rules:
            ty_rules[key] = value
            pyproject.changelog.append(f'Set tool.ty.rules.{key} = "{value}"')

    ty_rules = pyproject.get_table("tool.ty.rules", create=True)
    _remove_rule("unused-ignore-comment", "warn")
    _update_rule("division-by-zero", "warn")
    _update_rule("possibly-missing-import", "warn")
    _update_rule("possibly-unresolved-reference", "warn")

    ty_terminal = pyproject.get_table("tool.ty.terminal", create=True)
    if ty_terminal.get("error-on-warning") is not True:
        ty_terminal["error-on-warning"] = True
        pyproject.changelog.append("Set tool.ty.terminal.error-on-warning = true")


def _update_precommit_config(session: Session, /) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return
    existing_hook = find_hook(precommit.document, r"^ty$")
    exclude = existing_hook.get("exclude") if existing_hook else None
    precommit.remove_hook("ty", repo_url="local")
    hook = Hook(id="ty")
    if exclude:
        hook["exclude"] = exclude
    group = _select_dependency_group(pyproject)
    if group is not None:
        hook["args"] = read_preserved_yaml(f"[--group={group}, --no-default-groups]")
    expected_repo = Repo(
        repo="https://github.com/astral-sh/ty-pre-commit",
        rev="",
        hooks=[hook],
    )
    precommit.update_single_hook_repo(expected_repo)


def _select_dependency_group(pyproject: ModifiablePyproject) -> str | None:
    dependency_groups = pyproject.get_table("dependency-groups", fallback={})
    for group in ("types", "style", "typechecking"):
        if group in dependency_groups:
            return group
    return None


def _remove_ty(session: Session, /) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return
    config_path = Path("ty.toml")
    if config_path.exists():
        config_path.unlink()
        pyproject.changelog.append(f"Removed {config_path}")
    if pyproject.has_table("tool.ty"):
        del pyproject._document["tool"]["ty"]  # noqa: SLF001
        pyproject.changelog.append("Removed ty configuration table")
    pyproject.remove_dependency("ty")
    precommit.remove_hook("ty")
    remove_badge(
        session,
        badge_pattern=r".*https://.+\.com/astral\-sh/ty/main/assets/badge/v0\.json.*",
    )
