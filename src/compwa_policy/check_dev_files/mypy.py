"""Check and update :code:`mypy` settings."""

import os

import tomlkit
from ini2toml.api import Translator

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import PyprojectTOML


def main() -> None:
    pyproject = PyprojectTOML.load()
    executor = Executor()
    executor(_merge_mypy_into_pyproject, pyproject)
    executor(_update_vscode_settings, pyproject)
    executor(pyproject.finalize)
    executor.finalize()


def _update_vscode_settings(pyproject: PyprojectTOML) -> None:
    mypy_config = pyproject.get_table("tool.mypy")
    executor = Executor()
    if not mypy_config:
        executor(
            vscode.remove_extension_recommendation,
            "ms-python.mypy-type-checker",
            unwanted=True,
        )
        executor(vscode.remove_settings, ["mypy-type-checker.importStrategy"])
    else:
        executor(vscode.add_extension_recommendation, "ms-python.mypy-type-checker")
        settings = {
            "mypy-type-checker.args": [
                f"--config-file=${{workspaceFolder}}/{CONFIG_PATH.pyproject}"
            ],
            "mypy-type-checker.importStrategy": "fromEnvironment",
        }
        executor(vscode.update_settings, settings)
    executor.finalize()


def _merge_mypy_into_pyproject(pyproject: PyprojectTOML) -> None:
    config_path = ".mypy.ini"
    if not os.path.exists(config_path):
        return
    with open(config_path) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name=config_path)
    mypy_config = tomlkit.parse(toml_str)
    tool_table = pyproject.get_table("tool", create=True)
    tool_table.update(mypy_config)
    os.remove(config_path)
    msg = f"Moved mypy configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)
