"""Shared configuration for link checking with lychee."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomlkit
from packaging.requirements import Requirement
from packaging.version import Version

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.match import git_ls_files
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableMapping

    from compwa_policy.utilities.session import Session


# cspell:ignore elts mdwn mkdn mkdown
DEFAULT_EXTENSIONS = (
    "css",
    "htm",
    "html",
    "markdown",
    "md",
    "mdown",
    "mdwn",
    "mdx",
    "mkd",
    "mkdn",
    "mkdown",
    "txt",
    "xml",
)
"""Lychee's default extensions, which an explicit extensions option replaces."""
DOCUMENT_EXTENSIONS = ("ipynb", "qmd", "rst")
"""Documentation source formats that lychee does not scan by default."""


NOTEBOOK_REMAP = "^(.+)/n$ $1"
"""Strip the newline that lychee reads into URLs at the end of a notebook source line.

Lychee scans notebooks as plain text, so a URL at the end of a line in the JSON source
is followed by an escaped newline ``\n``, which lychee normalizes to ``/n``.
"""


def configure_lychee(
    config: ModifiablePyproject, /, session: Session | None = None
) -> None:
    if config._source == CONFIG_PATH.pyproject:  # ruff: ignore[private-member-access]
        _configure_pyproject(config)
    elif CONFIG_PATH.pyproject.exists():
        if session is not None:
            pyproject = session.pyproject
            if pyproject is not None:
                _configure_pyproject(pyproject)
        else:
            with ModifiablePyproject.load() as pyproject:
                _configure_pyproject(pyproject)
    else:
        path = Path("lychee.toml")
        document = tomlkit.loads(path.read_text() if path.exists() else "")
        changes = _update_options(document)
        if changes:
            path.write_text(tomlkit.dumps(document))
            config.changelog.extend(f"{msg} in lychee.toml" for msg in changes)


def _configure_pyproject(config: ModifiablePyproject) -> None:
    if config.has_table("tool.lychee"):
        config.changelog.extend(_update_options(config.get_table("tool.lychee")))
        return
    table = tomlkit.table()
    changes = _update_options(table)
    if changes:
        config.get_table("tool", create=True)["lychee"] = table
        config.changelog.extend(changes)


def _update_options(table: MutableMapping[str, Any]) -> list[str]:
    changes = []
    extra_extensions = {
        Path(path).suffix.removeprefix(".")
        for path in git_ls_files(*(f"*.{ext}" for ext in DOCUMENT_EXTENSIONS))
    }
    if _add_extensions(table, extra_extensions):
        changes.append("Configured lychee extensions")
    if "ipynb" in table.get("extensions", []) and _add_to_array(
        table, "remap", [NOTEBOOK_REMAP]
    ):
        changes.append("Remapped line breaks in notebook links for lychee")
    if "exclude" not in table and _add_to_array(
        table, "exclude", get_sphinx_linkcheck_ignore()
    ):
        changes.append("Excluded Sphinx linkcheck_ignore patterns from lychee")
    return changes


def _add_extensions(
    table: MutableMapping[str, Any], extra_extensions: set[str]
) -> bool:
    existing = list(table.get("extensions", DEFAULT_EXTENSIONS))
    missing = extra_extensions - set(existing)
    if not missing:
        return False
    table["extensions"] = to_toml_array([*existing, *sorted(missing)])
    return True


def _add_to_array(
    table: MutableMapping[str, Any], key: str, values: Iterable[str]
) -> bool:
    existing = list(table.get(key, []))
    missing = [value for value in values if value not in existing]
    if not missing:
        return False
    table[key] = to_toml_array([*existing, *missing])
    return True


def get_sphinx_linkcheck_ignore() -> list[str]:
    """Get the string patterns of ``linkcheck_ignore`` in Sphinx configurations.

    Both Sphinx and lychee interpret these patterns as regular expressions.
    """
    patterns: list[str] = []
    for path in git_ls_files("conf.py", "**/conf.py", ":!:tests"):
        module = ast.parse(Path(path).read_text())
        for node in module.body:
            if not isinstance(node, ast.Assign) or not isinstance(
                node.value, (ast.List, ast.Tuple)
            ):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "linkcheck_ignore"
                for target in node.targets
            ):
                continue
            patterns.extend(
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
    return patterns


def require_lychee(config: ModifiablePyproject, /, dependency_group: str) -> None:
    groups = config.get_table("dependency-groups", fallback={})
    visited: set[str] = set()

    def update(group: str) -> bool:
        if group in visited:
            return False
        visited.add(group)
        dependencies = groups.get(group, [])
        found = False
        for index, dependency in enumerate(dependencies):
            if not isinstance(dependency, str):
                found = update(dependency["include-group"]) or found
                continue
            requirement = Requirement(dependency)
            if requirement.name != "lychee-bin":
                continue
            found = True
            if any(
                spec.operator in {">=", ">", "~=", "=="}
                and Version(spec.version.rstrip(".*")) >= Version("0.24.0")
                for spec in requirement.specifier
            ):
                continue
            separator = "," if requirement.specifier else ""
            requirement.specifier = type(requirement.specifier)(
                f"{requirement.specifier}{separator}>=0.24.0"
            )
            dependencies[index] = str(requirement)
            config.changelog.append("Required lychee-bin>=0.24.0")
        return found

    if not update(dependency_group):
        config.add_dependency("lychee-bin>=0.24.0", dependency_group=dependency_group)
