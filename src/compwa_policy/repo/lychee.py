"""Shared configuration for Quarto link checking."""

from __future__ import annotations

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
    from collections.abc import MutableMapping

    from compwa_policy.utilities.session import Session


# cspell:ignore mdwn mkdn mkdown
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


def configure_lychee(
    config: ModifiablePyproject, /, session: Session | None = None
) -> None:
    extra_extensions = {
        Path(path).suffix.removeprefix(".") for path in git_ls_files("*.qmd")
    }
    if not extra_extensions:
        return
    if config._source == CONFIG_PATH.pyproject:  # ruff: ignore[private-member-access]
        _set_extensions(config, "tool.lychee", extra_extensions)
    elif CONFIG_PATH.pyproject.exists():
        if session is not None:
            pyproject = session.pyproject
            if pyproject is not None:
                _set_extensions(pyproject, "tool.lychee", extra_extensions)
        else:
            with ModifiablePyproject.load() as pyproject:
                _set_extensions(pyproject, "tool.lychee", extra_extensions)
    else:
        path = Path("lychee.toml")
        document = tomlkit.loads(path.read_text() if path.exists() else "")
        if _add_extensions(document, extra_extensions):
            path.write_text(tomlkit.dumps(document))
            config.changelog.append("Configured extensions in lychee.toml")


def _set_extensions(
    config: ModifiablePyproject, table_name: str, extra_extensions: set[str]
) -> None:
    table = config.get_table(table_name, create=True)
    if _add_extensions(table, extra_extensions):
        config.changelog.append("Configured lychee extensions")


def _add_extensions(
    table: MutableMapping[str, Any], extra_extensions: set[str]
) -> bool:
    existing = list(table.get("extensions", DEFAULT_EXTENSIONS))
    missing = extra_extensions - set(existing)
    if not missing:
        return False
    table["extensions"] = to_toml_array([*existing, *sorted(missing)])
    return True


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
