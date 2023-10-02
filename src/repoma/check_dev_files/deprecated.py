"""Remove deprecated linters and formatters."""
import os
import shutil
from typing import TYPE_CHECKING, List

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import remove_precommit_hook
from repoma.utilities.pyproject import load_pyproject, write_pyproject
from repoma.utilities.readme import remove_badge
from repoma.utilities.vscode import (
    remove_extension_recommendation,
    remove_settings,
)

if TYPE_CHECKING:
    from tomlkit.items import Table


def remove_deprecated_tools(keep_issue_templates: bool) -> None:
    executor = Executor()
    executor(_remove_flake8)
    executor(_remove_isort)
    if not keep_issue_templates:
        executor(_remove_github_issue_templates)
    executor(_remove_markdownlint)
    executor(_remove_pydocstyle)
    executor(_remove_pylint)
    executor.finalize()


def _remove_flake8() -> None:
    executor = Executor()
    executor(__remove_configs, [".flake8"])
    executor(__remove_nbqa_option, "flake8")
    executor(__uninstall, "flake8")
    executor(__uninstall, "pep8-naming")
    executor(remove_extension_recommendation, "ms-python.flake8", unwanted=True)
    executor(remove_precommit_hook, "autoflake")  # cspell:ignore autoflake
    executor(remove_precommit_hook, "flake8")
    executor(remove_precommit_hook, "nbqa-flake8")
    executor(remove_settings, ["flake8.importStrategy"])
    executor.finalize()


def _remove_isort() -> None:
    executor = Executor()
    executor(__remove_isort_settings)
    executor(__remove_nbqa_option, "black")
    executor(__remove_nbqa_option, "isort")
    executor(remove_extension_recommendation, "ms-python.isort", unwanted=True)
    executor(remove_precommit_hook, "isort")
    executor(remove_precommit_hook, "nbqa-isort")
    executor(remove_settings, ["isort.check", "isort.importStrategy"])
    executor(remove_badge, r".*https://img\.shields\.io/badge/%20imports\-isort")
    executor.finalize()


def __remove_isort_settings() -> None:
    pyproject = load_pyproject()
    if pyproject.get("tool", {}).get("isort") is None:
        return
    pyproject["tool"].remove("isort")  # type: ignore[union-attr]
    write_pyproject(pyproject)
    msg = f"Removed [tool.isort] section from {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def __remove_nbqa_option(option: str) -> None:
    pyproject = load_pyproject()
    # cspell:ignore addopts
    nbqa_table: Table = pyproject.get("tool", {}).get("nbqa", {}).get("addopts")
    if nbqa_table is None:
        return
    if nbqa_table.get(option) is None:
        return
    nbqa_table.remove(option)
    write_pyproject(pyproject)
    msg = f"Removed {option!r} nbQA options from {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _remove_github_issue_templates() -> None:
    __remove_configs(
        [
            ".github/ISSUE_TEMPLATE",
            ".github/pull_request_template.md",
        ]
    )


def _remove_markdownlint() -> None:
    executor = Executor()
    executor(__remove_configs, [".markdownlint.json", ".markdownlint.yaml"])
    executor(__remove_from_gitignore, ".markdownlint.json")
    executor(
        remove_extension_recommendation,
        # cspell:ignore davidanson markdownlint
        extension_name="davidanson.vscode-markdownlint",
        unwanted=True,
    )
    executor(remove_precommit_hook, "markdownlint")
    executor.finalize()


def _remove_pydocstyle() -> None:
    executor = Executor()
    executor(
        __remove_configs,
        [
            ".pydocstyle",
            "docs/.pydocstyle",
            "tests/.pydocstyle",
        ],
    )
    executor(__uninstall, "pydocstyle")
    executor(remove_precommit_hook, "pydocstyle")
    executor.finalize()


def _remove_pylint() -> None:
    executor = Executor()
    executor(__remove_configs, [".pylintrc"])  # cspell:ignore pylintrc
    executor(__uninstall, "pylint")
    executor(remove_extension_recommendation, "ms-python.pylint", unwanted=True)
    executor(remove_precommit_hook, "pylint")
    executor(remove_precommit_hook, "nbqa-pylint")
    executor(remove_settings, ["pylint.importStrategy"])
    executor.finalize()


def __remove_configs(paths: List[str]) -> None:
    executor = Executor()
    for path in paths:
        executor(__remove_file, path)
    executor.finalize()


def __remove_file(path: str) -> None:
    if not os.path.exists(path):
        return
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    msg = f"Removed {path}"
    raise PrecommitError(msg)


def __uninstall(package: str) -> None:
    if not os.path.exists(CONFIG_PATH.pyproject):
        return
    pyproject = load_pyproject()
    project = pyproject.get("project")
    if project is None:
        return
    updated = False
    dependencies = project.get("dependencies")
    if dependencies is not None and package in dependencies:
        dependencies.remove(package)
        updated = True
    optional_dependencies = project.get("optional-dependencies")
    if optional_dependencies is not None:
        for values in optional_dependencies.values():
            if package in values:
                values.remove(package)
                updated = True
    if updated:
        write_pyproject(pyproject)
        msg = f"Removed {package} from {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def __remove_from_gitignore(pattern: str) -> None:
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        return
    with open(gitignore_path) as f:
        lines = f.readlines()
    filtered_lines = [s for s in lines if pattern not in s]
    if filtered_lines == lines:
        return
    with open(gitignore_path, "w") as f:
        f.writelines(filtered_lines)
    msg = f"Removed {pattern} from {gitignore_path}"
    raise PrecommitError(msg)
