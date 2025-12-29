"""Check and update :code:`mypy` settings."""

import os

import rtoml
from ini2toml.api import Translator

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject


def main(active: bool, precommit: ModifiablePrecommit) -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_update_vscode_settings, active)
        if active:
            do(_merge_mypy_into_pyproject, pyproject)
        else:
            do(_remove_mypy, precommit, pyproject)


def _merge_mypy_into_pyproject(pyproject: ModifiablePyproject) -> None:
    old_config_path = ".mypy.ini"
    if not os.path.exists(old_config_path):
        return
    with open(old_config_path) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name=old_config_path)
    mypy_config = rtoml.loads(toml_str)
    tool_table = pyproject.get_table("tool", create=True)
    tool_table.update(mypy_config)
    os.remove(old_config_path)
    msg = f"Imported mypy configuration from {old_config_path}"
    pyproject.changelog.append(msg)


def _remove_mypy(
    precommit: ModifiablePrecommit, pyproject: ModifiablePyproject
) -> None:
    if pyproject.has_table("tool.mypy"):
        del pyproject._document["tool"]["mypy"]  # noqa: SLF001
        pyproject.changelog.append("Removed mypy configuration table")
    pyproject.remove_dependency("mypy")
    precommit.remove_hook("mypy")


def _update_vscode_settings(mypy: bool) -> None:
    with Executor() as do:
        if mypy:
            do(vscode.add_extension_recommendation, "ms-python.mypy-type-checker")
            settings = {
                "mypy-type-checker.args": [
                    f"--config-file=${{workspaceFolder}}/{CONFIG_PATH.pyproject}"
                ],
            }
            do(vscode.update_settings, settings)
        else:
            do(
                vscode.remove_extension_recommendation,
                "ms-python.mypy-type-checker",
                unwanted=True,
            )
            do(
                vscode.remove_settings,
                ["mypy-type-checker.args", "mypy-type-checker.importStrategy"],
            )
