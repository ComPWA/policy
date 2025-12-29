"""Check configuration of `Poe the Poet <https://poethepoet.natn.io>`_."""

from __future__ import annotations

from pathlib import Path

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, remove_lines
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject


def main(has_notebooks: bool) -> None:
    if not CONFIG_PATH.pyproject.is_file():
        return
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        if pyproject.has_table("tool.tox"):
            del pyproject._document["tool"]["tox"]  # noqa: SLF001
            msg = f"Removed deprecated tool.tox section from {CONFIG_PATH.pyproject}"
            pyproject.changelog.append(msg)
        if pyproject.has_table("tool.poe"):
            _check_expected_sections(pyproject, has_notebooks)
        do(remove_lines, CONFIG_PATH.gitignore, r"\.tox/?")
        pyproject.remove_dependency("poethepoet")
        pyproject.remove_dependency("tox")
        pyproject.remove_dependency("tox-uv")


def _check_expected_sections(pyproject: Pyproject, has_notebooks: bool) -> None:
    # cspell:ignore doclive docnb docnblive testenv
    table_name = "tool.poe.tasks"
    if not pyproject.has_table(table_name):
        return
    poe_table = pyproject.get_table(table_name)
    tasks = set(poe_table.get("env", set()))
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
    missing_tasks = expected_tasks - tasks
    if missing_tasks:
        msg = (
            f"Poe the Poet configuration is missing task definitions:"
            f" {', '.join(sorted(missing_tasks))}"
        )
        raise PrecommitError(msg)
