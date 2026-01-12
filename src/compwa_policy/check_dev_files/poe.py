"""Check configuration of `Poe the Poet <https://poethepoet.natn.io>`_."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, remove_lines
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    has_dependency,
)
from compwa_policy.utilities.toml import to_inline_table, to_toml_array

if TYPE_CHECKING:
    from compwa_policy.check_dev_files.conda import PackageManagerChoice


def main(has_notebooks: bool, package_manager: PackageManagerChoice) -> None:
    if not CONFIG_PATH.pyproject.is_file():
        return
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        if pyproject.has_table("tool.tox"):
            del pyproject._document["tool"]["tox"]  # noqa: SLF001
            msg = f"Removed deprecated tool.tox section from {CONFIG_PATH.pyproject}"
            pyproject.changelog.append(msg)
        if pyproject.has_table("tool.poe"):
            do(_check_expected_sections, pyproject, has_notebooks)
            if package_manager == "uv":
                do(_configure_uv_executor, pyproject)
                if pyproject.has_table("tool.poe.tasks"):
                    if has_dependency(pyproject, "jupyterlab"):
                        do(_set_jupyter_lab_task, pyproject)
                    do(_set_test_all, pyproject)
        do(remove_lines, CONFIG_PATH.gitignore, r"\.tox/?")
        pyproject.remove_dependency("poethepoet")
        pyproject.remove_dependency("tox")
        pyproject.remove_dependency("tox-uv")


def _check_expected_sections(pyproject: Pyproject, has_notebooks: bool) -> None:
    poe_table = pyproject.get_table("tool.poe")
    tasks = set(poe_table.get("tasks", set()))
    expected_tasks: set[str] = set()
    if Path("docs").exists():
        expected_tasks |= {
            "doc",
            "doclive",
        }
        if has_notebooks:
            expected_tasks |= {
                "docnb",
                "docnblive",
                "nb",
            }
    if Path("tests").exists():
        expected_tasks.add("test")
    missing_tasks = expected_tasks - tasks
    if missing_tasks:
        msg = (
            f"Poe the Poet configuration is missing task definitions:"
            f" {', '.join(sorted(missing_tasks))}"
        )
        raise PrecommitError(msg)


def _configure_uv_executor(pyproject: ModifiablePyproject) -> None:
    poe_table = pyproject.get_table("tool.poe")
    existing = poe_table.get("executor")
    if existing is not None and not isinstance(existing, Mapping):
        del poe_table["executor"]
    executor_config = dict(poe_table.get("executor", {}))
    updated = False
    if executor_config.get("type") != "uv":
        executor_config["type"] = "uv"
        updated = True
    if executor_config.get("isolated") is not True:
        executor_config["isolated"] = True
        updated = True
    if executor_config.get("no-group") != "dev":
        executor_config["no-group"] = "dev"
        updated = True
    if updated:
        poe_table["executor"] = executor_config
        msg = f"Set Poe the Poet executor to uv in {CONFIG_PATH.pyproject}"
        pyproject.changelog.append(msg)


def _set_jupyter_lab_task(pyproject: ModifiablePyproject) -> None:
    tasks = pyproject.get_table("tool.poe.tasks")
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


def _set_test_all(pyproject: ModifiablePyproject) -> None:
    supported_python_versions = pyproject.get_supported_python_versions()
    if len(supported_python_versions) <= 1:
        return
    tasks = pyproject.get_table("tool.poe.tasks")
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
