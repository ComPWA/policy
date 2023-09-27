"""Remove deprecated linters and formatters."""
import os
from typing import TYPE_CHECKING, List

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import remove_precommit_hook
from repoma.utilities.pyproject import load_pyproject, write_pyproject
from repoma.utilities.readme import remove_badge
from repoma.utilities.setup_cfg import open_setup_cfg
from repoma.utilities.vscode import (
    remove_extension_recommendation,
    remove_settings,
)

if TYPE_CHECKING:
    from tomlkit.items import Table


def remove_deprecated_tools() -> None:
    executor = Executor()
    executor(_remove_flake8)
    executor(_remove_isort)
    executor(_remove_pydocstyle)
    executor(_remove_pylint)
    executor.finalize()


def _remove_flake8() -> None:
    executor = Executor()
    executor(__remove_configs, [".flake8"])
    executor(__remove_nbqa_option, "flake8")
    executor(__uninstall, "flake8", check_options=["lint", "sty"])
    executor(__uninstall, "pep8-naming", check_options=["lint", "sty"])
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
    executor(__uninstall, "pydocstyle", check_options=["lint", "sty"])
    executor(remove_precommit_hook, "pydocstyle")
    executor.finalize()


def _remove_pylint() -> None:
    executor = Executor()
    executor(__remove_configs, [".pylintrc"])  # cspell:ignore pylintrc
    executor(__uninstall, "pylint", check_options=["lint", "sty"])
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
    os.remove(path)
    msg = f"Removed {path}"
    raise PrecommitError(msg)


def __uninstall(package: str, check_options: List[str]) -> None:
    if not os.path.exists(CONFIG_PATH.setup_cfg):
        return
    cfg = open_setup_cfg()
    section = "options.extras_require"
    if not cfg.has_section(section):
        return
    for option in check_options:
        if not cfg.has_option(section, option):
            continue
        if package not in cfg.get(section, option):
            continue
        msg = f'Please remove {package} from the "{section}" section of setup.cfg'
        raise PrecommitError(msg)
