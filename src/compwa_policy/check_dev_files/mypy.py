"""Check and update :code:`mypy` settings."""

import os

import rtoml
from ini2toml.api import Translator
from ruamel.yaml.comments import CommentedSeq

from compwa_policy.utilities import CONFIG_PATH, remove_lines, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.readme import add_badge, remove_badge


def main(active: bool, precommit: ModifiablePrecommit) -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_update_vscode_settings, active)
        if active:
            pyproject.add_dependency("mypy", dependency_group=["style", "dev"])
            do(_merge_mypy_into_pyproject, pyproject)
            do(_update_precommit_config, precommit)
            do(remove_badge, r"http://(www\.)?mypy\-lang\.org/")
            do(
                add_badge,
                "[![Type-checked with mypy](https://mypy-lang.org/static/mypy_badge.svg)](https://mypy.readthedocs.io)",
            )
        else:
            do(_remove_mypy, precommit, pyproject)
            do(remove_lines, CONFIG_PATH.gitignore, ".*mypy.*")


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
    remove_badge(r"\[\!\[.*[Mm]ypy.*\]\(.*mypy.*\)\]\(.*mypy.*\)\n?")


def _update_precommit_config(precommit: ModifiablePrecommit) -> None:
    types = CommentedSeq(["python"])
    types.fa.set_flow_style()
    hook = Hook(
        id="mypy",
        name="mypy",
        entry="mypy",
        language="system",
        require_serial=True,
        types=types,
    )
    expected_repo = Repo(repo="local", hooks=[hook])
    precommit.update_single_hook_repo(expected_repo)


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
