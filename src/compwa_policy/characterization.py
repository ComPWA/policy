"""Detect tooling and content present in a repository."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import rtoml
import yaml

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.match import is_committed

if TYPE_CHECKING:
    from compwa_policy.config import PackageManagerChoice, TypeChecker


@dataclass(frozen=True)
class RepositoryCharacterization:
    """The repository traits that influence policy configuration."""

    has_python_code: bool
    package_manager: PackageManagerChoice
    type_checkers: frozenset[TypeChecker]


@cache
def has_documentation() -> bool:
    if is_committed("docs/**", untracked=True):
        return True
    if is_committed("_quarto.yml", "**/_quarto.yml", ":!:tests", untracked=True):
        return True
    return is_committed("conf.py", "**/conf.py", ":!:tests", untracked=True)


@cache
def has_notebooks() -> bool:
    return is_committed("*.ipynb", "**/*.ipynb", untracked=True)


@cache
def has_python_code() -> bool:
    return is_committed(
        "*.ipynb",
        "**/*.ipynb",
        "*.py",
        "**/*.py",
        "*.pyi",
        "**/*.pyi",
        untracked=True,
    )


def characterize_repository() -> RepositoryCharacterization:
    pyproject = _load_pyproject()
    return RepositoryCharacterization(
        has_python_code=has_python_code(),
        package_manager=detect_package_manager(pyproject),
        type_checkers=frozenset(detect_type_checkers(pyproject)),
    )


def detect_package_manager(
    pyproject: dict[str, Any] | None = None,
) -> PackageManagerChoice:
    """Infer the active Python environment/package manager from its configuration."""
    if pyproject is None:
        pyproject = _load_pyproject()
    has_pixi = _has_file("pixi.toml", "pixi.lock") or _has_table(pyproject, "tool.pixi")
    has_uv = _has_file("uv.lock") or _has_table(pyproject, "tool.uv")
    if has_pixi and has_uv:
        return "pixi+uv"
    if has_pixi:
        return "pixi"
    if has_uv:
        return "uv"
    if _has_file("environment.yml", "environment.yaml", "conda-lock.yml"):
        return "conda"
    return "none"


def detect_type_checkers(
    pyproject: dict[str, Any] | None = None,
) -> set[TypeChecker]:
    """Infer configured type checkers from files, TOML tables, and pre-commit hooks."""
    if pyproject is None:
        pyproject = _load_pyproject()
    detected: set[TypeChecker] = set()
    markers: dict[TypeChecker, tuple[str, ...]] = {
        "mypy": (".mypy.ini", "mypy.ini"),
        "pyright": ("pyrightconfig.json",),
        "ty": ("ty.toml",),
    }
    for checker, files in markers.items():
        if _has_file(*files) or _has_table(pyproject, f"tool.{checker}"):
            detected.add(checker)
    hook_ids = _precommit_hook_ids()
    detected.update(checker for checker in markers if checker in hook_ids)
    return detected


def _has_file(*paths: str) -> bool:
    return any(Path(path).exists() for path in paths)


def _has_table(document: dict[str, Any], dotted_key: str) -> bool:
    current: object = document
    for key in dotted_key.split("."):
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return isinstance(current, dict)


def _load_pyproject() -> dict[str, Any]:
    if not CONFIG_PATH.pyproject.exists():
        return {}
    return rtoml.load(CONFIG_PATH.pyproject)


def _precommit_hook_ids() -> set[str]:
    if not CONFIG_PATH.precommit.exists():
        return set()
    document = yaml.safe_load(CONFIG_PATH.precommit.read_text()) or {}
    return {
        hook["id"]
        for repo in document.get("repos", [])
        for hook in repo.get("hooks", [])
        if "id" in hook
    }
