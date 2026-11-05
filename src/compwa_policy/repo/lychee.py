"""Shared configuration for repositories that use lychee."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomlkit
from packaging.requirements import Requirement
from packaging.version import Version

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.match import git_ls_files
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableMapping

    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.resource import Changelog
    from compwa_policy.utilities.session import Session


_BASELINE = {
    "cache": True,
    "cache_exclude_status": "400..",
    "hidden": True,
    "include_fragments": "anchor-only",
    "include_verbatim": True,
    "max_cache_age": "7d",
}


@check_hook(group="repo", paths=[CONFIG_PATH.pyproject, "pixi.toml", "lychee.toml"])
def check(session: Session, _args: Arguments, _ctx: CheckContext) -> None:
    pyproject = session.pyproject
    configs = [pyproject] if pyproject is not None else []
    if Path("pixi.toml").exists():
        configs.append(session.pixi)
    if not configs:
        if Path("lychee.toml").exists():
            _configure_standalone(set(), session.changelog)
        return
    if (
        Path("lychee.toml").exists()
        or any(config.has_table("tool.lychee") for config in configs)
        or any(_has_lychee_task(config) for config in configs)
    ):
        configure_lychee(configs[0], session)


def _has_lychee_task(config: ModifiablePyproject) -> bool:
    poe = config.get_table("tool.poe", fallback={})
    prefix = "" if config._source == CONFIG_PATH.pixi_toml else "tool.pixi."  # ruff: ignore[private-member-access]
    tables = [
        poe.get("tasks", {}),
        *(group.get("tasks", {}) for group in poe.get("groups", {}).values()),
        config.get_table(f"{prefix}tasks", fallback={}),
        *(
            feature.get("tasks", {})
            for feature in config.get_table(f"{prefix}feature", fallback={}).values()
        ),
    ]
    return any(_runs_lychee(task) for table in tables for task in table.values())


def _runs_lychee(task: Any) -> bool:
    """Recognize lychee commands without mistaking package names for commands.

    >>> _runs_lychee({"cmd": ["uvx", "lychee@0.24", "."]})
    True
    >>> _runs_lychee({"sequence": [{"shell": "lychee ."}]})
    True
    >>> _runs_lychee("echo lychee-bin")
    False
    """
    if isinstance(task, str):
        return re.search(r"(?:^|[\s/])lychee(?:@[^\s]+)?(?:\s|$)", task) is not None
    if isinstance(task, Mapping):
        return any(_runs_lychee(task.get(key)) for key in ("cmd", "shell", "sequence"))
    if isinstance(task, Sequence):
        return any(_runs_lychee(item) for item in task)
    return False


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
LYCHEE_MINIMUM_VERSION = "0.24.0"
LYCHEE_REQUIREMENT = f"lychee-bin>={LYCHEE_MINIMUM_VERSION}"


def uses_lychee(session: Session) -> bool:
    """Detect lychee configuration or a Poe/Pixi linkcheck task in this session."""
    if any(Path(name).exists() for name in ("lychee.toml", ".lychee.toml")):
        return True
    configs = [session.pyproject] if session.pyproject is not None else []
    if CONFIG_PATH.pixi_toml.exists():
        configs.append(session.pixi)
    return any(
        config.has_table("tool.lychee") or _has_lychee_task(config)
        for config in configs
    )


def configure_lychee(
    config: ModifiablePyproject, /, session: Session | None = None
) -> None:
    extra_extensions = {
        Path(path).suffix.removeprefix(".") for path in git_ls_files("*.qmd")
    }
    if Path("lychee.toml").exists():
        _configure_standalone(extra_extensions, config.changelog)
    elif config._source == CONFIG_PATH.pyproject:  # ruff: ignore[private-member-access]
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
        _configure_standalone(extra_extensions, config.changelog)


def _configure_standalone(extra_extensions: set[str], changelog: Changelog) -> None:
    path = Path("lychee.toml")
    document = tomlkit.loads(path.read_text() if path.exists() else "")
    if _configure_table(document, extra_extensions):
        path.write_text(tomlkit.dumps(document))
        changelog.append("Configured lychee.toml")


def _set_extensions(
    config: ModifiablePyproject, table_name: str, extra_extensions: set[str]
) -> None:
    table = config.get_table(table_name, create=True)
    if _configure_table(table, extra_extensions):
        config.changelog.append("Configured lychee settings")


def _configure_table(
    table: MutableMapping[str, Any], extra_extensions: set[str]
) -> bool:
    changed = _add_extensions(table, extra_extensions)
    for key, value in _BASELINE.items():
        if table.get(key) != value:
            table[key] = value
            changed = True
    return changed


def _add_extensions(
    table: MutableMapping[str, Any], extra_extensions: set[str]
) -> bool:
    existing = list(table.get("extensions", DEFAULT_EXTENSIONS))
    missing = extra_extensions - set(existing)
    if not missing:
        return False
    table["extensions"] = to_toml_array([*existing, *sorted(missing)])
    return True


def require_lychee(config: ModifiablePyproject, /, group: str) -> None:
    groups = config.get_table("dependency-groups", fallback={})
    visited: set[str] = set()

    def update(group_name: str) -> bool:
        if group_name in visited:
            return False
        visited.add(group_name)
        dependencies = groups.get(group_name, [])
        found = False
        for index, dependency in enumerate(dependencies):
            if not isinstance(dependency, str):
                found = update(dependency["include-group"]) or found
                continue
            if Requirement(dependency).name != "lychee-bin":
                continue
            found = True
            required = _require_minimum_version(dependency)
            if required != dependency:
                dependencies[index] = required
                config.changelog.append(f"Required {LYCHEE_REQUIREMENT}")
        return found

    if not update(group):
        config.add_dependency(LYCHEE_REQUIREMENT, group=group)


def require_lychee_in_with(dependencies: str | Iterable[str] | None) -> list[str]:
    """Require lychee in the ``with`` dependencies of a Poe task executor.

    >>> require_lychee_in_with(None)
    ['lychee-bin>=0.24.0']
    >>> require_lychee_in_with("sphinx")
    ['sphinx', 'lychee-bin>=0.24.0']
    >>> require_lychee_in_with(["lychee-bin>=0.20,<1"])
    ['lychee-bin<1,>=0.20,>=0.24.0']
    >>> require_lychee_in_with(["lychee-bin>=0.25"])
    ['lychee-bin>=0.25']
    """
    if dependencies is None:
        dependencies = []
    elif isinstance(dependencies, str):
        dependencies = [dependencies]
    required = [
        _require_minimum_version(dependency)
        if Requirement(dependency).name == "lychee-bin"
        else dependency
        for dependency in dependencies
    ]
    if not any(Requirement(dependency).name == "lychee-bin" for dependency in required):
        required.append(LYCHEE_REQUIREMENT)
    return required


def _require_minimum_version(dependency: str) -> str:
    requirement = Requirement(dependency)
    if any(
        spec.operator in {">=", ">", "~=", "=="}
        and Version(spec.version.rstrip(".*")) >= Version(LYCHEE_MINIMUM_VERSION)
        for spec in requirement.specifier
    ):
        return dependency
    separator = "," if requirement.specifier else ""
    requirement.specifier = type(requirement.specifier)(
        f"{requirement.specifier}{separator}>={LYCHEE_MINIMUM_VERSION}"
    )
    return str(requirement)
