"""Check configuration of `Poe the Poet <https://poethepoet.natn.io>`_."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import tomlkit

from compwa_policy._characterization import has_documentation
from compwa_policy.errors import PolicyError
from compwa_policy.utilities import CONFIG_PATH, remove_lines
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.match import git_ls_files, is_committed
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    has_dependency,
)
from compwa_policy.utilities.toml import to_inline_table, to_toml_array

if TYPE_CHECKING:
    from tomlkit.items import Array, Table

    from compwa_policy import Arguments
    from compwa_policy.config import PackageManagerChoice
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Changelog, Session


_DOC_TASKS = frozenset({
    "doc",
    "doclive",
    "docnb",
    "docnb-force",
    "docnblive",
    "linkcheck",
})
_NOTEBOOK_TASKS = frozenset({"lab", "nb"})
_TEST_TASKS = frozenset({"benchmark", "cov", "test", "test-all"})
_TEST_PY_PATTERN = re.compile(r"^test-py3\d+$")


@check_hook(
    group="repo",
    paths=[CONFIG_PATH.pyproject, CONFIG_PATH.gitignore, CONFIG_PATH.precommit],
    patterns=("(.*/)?_quarto\\.yml",),
)
def check(session: Session, args: Arguments, ctx: CheckContext) -> None:
    config = session.pyproject
    if config is None:
        return
    if config.has_table("tool.tox"):
        del config._document["tool"]["tox"]  # noqa: SLF001
        msg = f"Removed deprecated tool.tox section from {CONFIG_PATH.pyproject}"
        config.changelog.append(msg)
    if config.has_table("tool.poe"):
        _check_expected_sections(config, ctx.has_notebooks)
        if args.package_manager == "uv":
            _configure_uv_executor(config)
            _migrate_tasks_to_groups(config)
            _set_doc_group(config)
            _set_test_group(config)
            _set_notebook_group(config, ctx.has_notebooks)
            _check_no_uv_run(config)
            if config.has_table("tool.poe.tasks"):
                _set_all_task(config)
            if has_dependency(config, "jupyterlab"):
                _set_jupyter_lab_task(config)
            if ctx.has_notebooks:
                config.remove_dependency("nbmake")  # cspell:ignore nbmake
                _set_nb_task(config)
            _set_test_all_task(config)
            _update_doclive(config)
        if config.has_table("tool.poe.tasks"):
            _set_upgrade_task(config, args.package_manager)
    remove_lines(session, CONFIG_PATH.gitignore, pattern=r"\.tox/?")
    config.remove_dependency("poethepoet")
    config.remove_dependency("tox")
    config.remove_dependency("tox-uv")


def _get_all_poe_tasks(poe_table: Mapping) -> set[str]:
    tasks: set[str] = set(poe_table.get("tasks", {}))
    for group_config in poe_table.get("groups", {}).values():
        tasks |= set(group_config.get("tasks", {}))
    return tasks


def _check_expected_sections(pyproject: Pyproject, has_notebooks: bool) -> None:
    poe_table = pyproject.get_table("tool.poe")
    tasks = _get_all_poe_tasks(poe_table)
    expected_tasks: set[str] = set()
    if has_documentation():
        expected_tasks |= {
            "doc",
            "doclive",
        }
        if has_notebooks:
            expected_tasks.add("nb")
        if has_dependency(pyproject, "myst-nb"):
            expected_tasks.update({"docnb", "docnblive"})
    if Path("tests").exists():
        expected_tasks.add("test")
    missing_tasks = expected_tasks - tasks
    if missing_tasks:
        msg = (
            f"Poe the Poet configuration is missing task definitions:"
            f" {', '.join(sorted(missing_tasks))}"
        )
        raise PolicyError(msg)


def _configure_uv_executor(pyproject: ModifiablePyproject, /) -> None:
    poe_table = pyproject.get_table("tool.poe")
    executor_table = poe_table.get("executor")
    if executor_table is None or isinstance(executor_table, str):
        if "executor" in poe_table:
            del poe_table["executor"]
        executor_table = {}
    has_dev = "dev" in pyproject.get_table("dependency-groups", fallback=set())
    if any([
        __safe_update(executor_table, "isolated", True),
        __safe_update(executor_table, "no-group", "dev") if has_dev else False,
        __safe_update(executor_table, "type", "uv"),
    ]):
        poe_table["executor"] = executor_table
        msg = f"Set Poe the Poet executor to uv in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _get_or_create_group_tasks(
    pyproject: ModifiablePyproject, group_name: str
) -> MutableMapping[str, Any]:
    """Get or create the tasks table for a Poe group as a super-table.

    Using ``create=True`` on ``get_table`` creates the last element as a regular
    table, which causes tomlkit to emit an explicit empty ``[...tasks]`` header.
    Creating it manually as a super-table avoids that spurious header.
    """
    group = pyproject.get_table(f"tool.poe.groups.{group_name}", create=True)
    if "tasks" not in group:
        group["tasks"] = tomlkit.table(is_super_table=True)
    return group["tasks"]


def _migrate_tasks_to_groups(pyproject: ModifiablePyproject, /) -> None:
    """Move any doc/test tasks from tool.poe.tasks into their group sub-tables."""
    if not pyproject.has_table("tool.poe.tasks"):
        return
    tasks = pyproject.get_table("tool.poe.tasks")
    migrated: Changelog = []
    for task_name in list(tasks.keys()):
        target_group = None
        if task_name in _DOC_TASKS:
            target_group = "doc"
        elif task_name in _TEST_TASKS or _TEST_PY_PATTERN.match(task_name):
            target_group = "test"
        elif task_name in _NOTEBOOK_TASKS:
            target_group = "notebook"
        if target_group is not None:
            group_tasks = _get_or_create_group_tasks(pyproject, target_group)
            group_tasks[task_name] = tasks[task_name]
            del tasks[task_name]
            migrated.append(task_name)
    if migrated:
        msg = (
            f"Moved Poe the Poet tasks to groups in {CONFIG_PATH.pyproject}:"
            f" {', '.join(sorted(migrated))}"
        )
        pyproject.changelog.append(msg)


def _set_doc_group(pyproject: ModifiablePyproject, /) -> None:
    if not has_documentation():
        return
    doc_group = pyproject.get_table("tool.poe.groups.doc", create=True)
    if __safe_update(doc_group, "heading", "Documentation"):
        msg = f"Set Poe the Poet doc group heading in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _set_test_group(pyproject: ModifiablePyproject, /) -> None:
    if not Path("tests").exists():
        return
    test_group = pyproject.get_table("tool.poe.groups.test", create=True)
    if __safe_update(test_group, "heading", "Testing"):
        msg = f"Set Poe the Poet test group heading in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _set_notebook_group(pyproject: ModifiablePyproject, /, has_notebooks: bool) -> None:
    if not has_notebooks and not has_dependency(pyproject, "jupyterlab"):
        return
    notebook_group = pyproject.get_table("tool.poe.groups.notebook", create=True)
    if __safe_update(notebook_group, "heading", "Notebooks"):
        msg = f"Set Poe the Poet notebook group heading in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _check_no_uv_run(pyproject: Pyproject) -> None:
    poe_table = pyproject.get_table("tool.poe")
    all_task_tables: list[Mapping] = [
        poe_table.get("tasks", {}),
        *(
            group_config.get("tasks", {})
            for group_config in poe_table.get("groups", {}).values()
        ),
    ]
    offending_tasks = []
    for task_table in all_task_tables:
        for name, task in task_table.items():
            if __has_uv_run(task.get("cmd", "")) and task.get("executor") != "simple":
                offending_tasks.append(name)
    if offending_tasks:
        msg = (
            "Poe the Poet tasks should not use 'uv run' when the executor is set to"
            " 'uv'. Offending tasks: "
            f"{', '.join(sorted(offending_tasks))}"
        )
        raise PolicyError(msg)


def __has_uv_run(cmd: str | Sequence) -> bool:
    """Check whether a Poe task command shells out to :code:`uv run`.

    >>> __has_uv_run("uv run pytest")
    True
    >>> __has_uv_run(["python", "-m", "pytest"])
    False
    >>> __has_uv_run(["uv run pytest", "coverage report"])
    True
    """
    if isinstance(cmd, str):
        return "uv run" in cmd
    if isinstance(cmd, Sequence):
        return any(__has_uv_run(part) for part in cmd)
    return False


def _set_all_task(pyproject: ModifiablePyproject, /) -> None:
    task_table = pyproject.get_table("tool.poe.tasks")
    if "all" not in task_table:
        return
    all_task = cast("Table", task_table["all"])
    sequence = all_task.get("sequence")
    delegates_to_tasks = isinstance(sequence, Sequence) and all(
        isinstance(item, str) or (isinstance(item, Mapping) and "ref" in item)
        for item in sequence
    )
    if any([
        __safe_update(
            all_task, "help", "Run all continuous integration (CI) tasks locally"
        ),
        __safe_update(all_task, "ignore_fail", "return_non_zero")
        if not delegates_to_tasks
        else False,
    ]):
        msg = f"Updated Poe the Poet all task in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _set_jupyter_lab_task(pyproject: ModifiablePyproject, /) -> None:
    tasks = _get_or_create_group_tasks(pyproject, "notebook")
    existing = cast("Mapping", tasks.get("lab", {}))
    expected = {
        "args": to_toml_array([{"name": "paths", "default": "", "positional": True}]),
        "cmd": "jupyter lab ${paths}",
        "help": "Launch Jupyter Lab",
    }
    if isinstance(executor := existing.get("executor"), Mapping):
        expected["executor"] = executor
    elif "jupyter" in set(pyproject.get_table("dependency-groups", fallback=set())):
        expected["executor"] = to_inline_table({"group": "jupyter"})
    if existing != expected:
        tasks["lab"] = expected
        msg = f"Set Poe the Poet jupyter task in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _set_nb_task(pyproject: ModifiablePyproject, /) -> None:
    tasks = _get_or_create_group_tasks(pyproject, "notebook")
    existing = cast("Table", tasks.get("nb", {}))
    expected = {
        "args": to_toml_array([
            {
                "name": "paths",
                "default": __get_notebook_path(),
                "multiple": True,
                "positional": True,
            }
        ]),
        "cmd": "pytest --nbmake --nbmake-timeout=0 ${paths}",
        "help": "Run all notebooks",
    }
    executor = {}
    if "notebooks" in pyproject.get_table("dependency-groups", fallback=set()):
        executor["group"] = "notebooks"
    existing_executor_with = existing.get("executor", {}).get("with")
    if existing_executor_with is not None and existing_executor_with not in (
        "nbmake",
        ["nbmake"],
    ):
        if isinstance(existing_executor_with, str):
            existing_executor_with = [existing_executor_with]
        if "nbmake" not in existing_executor_with:
            existing_executor_with.append("nbmake")
        executor["with"] = existing_executor_with
    else:
        executor["with"] = "nbmake"
    expected["executor"] = to_inline_table(executor)
    if existing != expected:
        tasks["nb"] = expected
        msg = f"Set Poe the Poet nb task in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def __get_notebook_path() -> str:
    notebooks = git_ls_files("**/*.ipynb")
    if not notebooks:
        return ""
    return os.path.commonpath(os.path.dirname(p) for p in notebooks)


def _set_test_all_task(pyproject: ModifiablePyproject, /) -> None:
    supported_python_versions = pyproject.get_supported_python_versions()
    if len(supported_python_versions) <= 1:
        return
    if not pyproject.has_table("tool.poe.groups.test.tasks"):
        return
    tasks = pyproject.get_table("tool.poe.groups.test.tasks")
    if "test" not in tasks:
        return
    if "test-py" in tasks:
        del tasks["test-py"]
        pyproject.changelog.append(
            f"Removed deprecated Poe the Poet task test-py in {CONFIG_PATH.pyproject}"
        )
    existing = {
        name: task
        for name, task in tasks.items()
        if name == "test-all" or re.match(r"^test-py3\d+$", name)
    }
    expected = {}
    expected["test-all"] = {
        "help": "Run all tests on each supported Python version",
        "sequence": to_toml_array([
            {"ref": f"test-py{version.replace('.', '')} ${{paths}}"}
            for version in supported_python_versions
        ]),
        "args": [
            {
                "default": "",
                "multiple": True,
                "name": "paths",
                "positional": True,
            }
        ],
    }
    expected.update({
        f"test-py{version.replace('.', '')}": {
            "env": to_inline_table({"UV_PYTHON": version}),
            "ref": "test",
        }
        for version in supported_python_versions
    })
    if existing != expected:
        for name in existing:
            del tasks[name]
        for name, task in expected.items():
            tasks[name] = task
        msg = f"Updated Poe the Poet test-all task in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _set_upgrade_task(
    pyproject: ModifiablePyproject, package_manager: PackageManagerChoice
) -> None:
    tasks = pyproject.get_table("tool.poe.tasks")
    parallel_cmds = []
    if is_committed(".pre-commit-config.yaml"):
        parallel_cmds.append({"cmd": "pre-commit autoupdate -j8"})
    if "uv" in package_manager:
        parallel_cmds.append({"cmd": "uv lock --upgrade"})
    if "pixi" in package_manager:
        parallel_cmds.append({"cmd": "pixi upgrade"})
    if not parallel_cmds:
        if "upgrade" in tasks:
            del tasks["upgrade"]
            msg = f"Removed Poe the Poet upgrade task from {CONFIG_PATH.pyproject}"
            pyproject.changelog.append(msg)
        return
    existing = cast("Mapping", tasks.get("upgrade", {}))
    expected = {
        "executor": to_inline_table({"type": "simple"}),
        "help": "Upgrade lock files",
        "parallel": to_toml_array(parallel_cmds),
    }
    if existing != expected:
        tasks["upgrade"] = expected
        msg = f"Set Poe the Poet upgrade task in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _update_doclive(pyproject: ModifiablePyproject, /) -> None:
    def combine(key: str, value: str) -> str | Array:
        existing_value = executor.get(key)
        if existing_value is None or existing_value == value:
            return value
        if isinstance(existing_value, str):
            existing_value = [existing_value]
        return to_toml_array(sorted({*existing_value, value}), multiline=False)

    if not pyproject.has_table("tool.poe.groups.doc.tasks"):
        return
    tasks = pyproject.get_table("tool.poe.groups.doc.tasks")
    if "doclive" not in tasks:
        return
    doclive_task = cast("Table", tasks["doclive"])
    executor = cast("dict[str, Any]", doclive_task.get("executor", {}))
    if "doc" in pyproject.get_table("dependency-groups", fallback=set()):
        executor["group"] = combine("group", "doc")
    if "sphinx-autobuild" in doclive_task.get("cmd", ""):
        executor["with"] = combine("with", "sphinx-autobuild")
        pyproject.remove_dependency("sphinx-autobuild")  # cspell:ignore autobuild
    if any([
        __safe_update(doclive_task, "executor", to_inline_table(executor))
        if executor
        else False,
        __safe_update(
            doclive_task,
            "help",
            "Set up a server to directly preview changes to the HTML pages",
        ),
    ]):
        msg = f"Updated Poe the Poet doclive task in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def __safe_update(table: MutableMapping, key: str, expected_value: Any) -> bool:
    if table.get(key) != expected_value:
        table[key] = expected_value
        return True
    return False
