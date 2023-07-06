"""Check and update :code:`mypy` settings."""
import os

import tomlkit
from ini2toml.api import Translator

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.pyproject import get_sub_table, load_pyproject, write_pyproject
from repoma.utilities.vscode import (
    add_extension_recommendation,
    remove_extension_recommendation,
    remove_settings,
    set_setting,
)


def main() -> None:
    executor = Executor()
    executor(_merge_mypy_into_pyproject)
    executor(_update_vscode_settings)
    executor.finalize()


def _update_vscode_settings() -> None:
    pyproject = load_pyproject()
    mypy_config = pyproject.get("tool", {}).get("mypy")
    executor = Executor()
    if mypy_config is None:
        executor(
            remove_extension_recommendation,
            "ms-python.mypy-type-checker",
            unwanted=True,
        )
        executor(remove_settings, ["mypy-type-checker.importStrategy"])
    else:
        executor(add_extension_recommendation, "ms-python.mypy-type-checker")
        settings = {
            "mypy-type-checker.importStrategy": "fromEnvironment",
            "python.linting.mypyEnabled": False,
        }
        executor(set_setting, settings)
    executor.finalize()


def _merge_mypy_into_pyproject() -> None:
    config_path = ".mypy.ini"
    if not os.path.exists(config_path):
        return
    with open(config_path) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name=config_path)
    mypy_config = tomlkit.parse(toml_str)
    pyproject = load_pyproject()
    tool_table = get_sub_table(pyproject, "tool", create=True)
    tool_table.update(mypy_config)
    write_pyproject(pyproject)
    os.remove(config_path)
    msg = f"Moved mypy configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)
