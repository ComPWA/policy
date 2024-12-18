"""Update :file:`pyproject.toml` black configuration."""

from typing import Any

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import ModifiablePyproject, complies_with_subset
from compwa_policy.utilities.toml import to_toml_array
from compwa_policy.utilities.yaml import read_preserved_yaml


def main(precommit: ModifiablePrecommit, has_notebooks: bool) -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_remove_outdated_settings, pyproject)
        do(_update_black_settings, pyproject)
        do(
            precommit.remove_hook,
            hook_id="black",
            repo_url="https://github.com/psf/black",
        )
        do(
            precommit.remove_hook,
            hook_id="black-jupyter",
            repo_url="https://github.com/psf/black",
        )
        do(_update_precommit_repo, precommit, has_notebooks)
        do(vscode.add_extension_recommendation, "ms-python.black-formatter")
        do(
            vscode.update_settings,
            {"black-formatter.importStrategy": "fromEnvironment"},
        )
        do(
            vscode.update_settings,
            {
                "[python]": {
                    "editor.defaultFormatter": "ms-python.black-formatter",
                    "editor.rulers": [88],
                },
            },
        )
        do(precommit.remove_hook, "nbqa-black")


def _remove_outdated_settings(pyproject: ModifiablePyproject) -> None:
    settings = pyproject.get_table("tool.black", create=True)
    forbidden_options = ("line-length",)
    removed_options = set()
    for option in forbidden_options:
        if option in settings:
            settings.pop(option)
            removed_options.add(option)
    if removed_options:
        msg = f"Removed {', '.join(sorted(removed_options))} option from black configuration"
        pyproject.changelog.append(msg)


def _update_black_settings(pyproject: ModifiablePyproject) -> None:
    settings = pyproject.get_table("tool.black", create=True)
    minimal_settings: dict[str, Any] = {"preview": True}
    project_root = pyproject.get_table("project", create=True)
    if "requires-python" in project_root:
        if settings.get("target-version") is not None:
            settings.pop("target-version")
            msg = "Removed target-version from black configuration"
            pyproject.changelog.append(msg)
    else:
        versions = pyproject.get_supported_python_versions()
        target_version = to_toml_array(
            sorted("py" + v.replace(".", "") for v in versions)
        )
        minimal_settings["target-version"] = target_version
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        msg = "Updated black configuration"
        pyproject.changelog.append(msg)


def _update_precommit_repo(precommit: ModifiablePrecommit, has_notebooks: bool) -> None:
    expected_repo = Repo(
        repo="https://github.com/psf/black-pre-commit-mirror",
        rev="",
        hooks=[Hook(id="black")],
    )
    if has_notebooks:
        black_jupyter = Hook(
            id="black-jupyter",
            args=read_preserved_yaml("[--line-length=85]"),
            types_or=read_preserved_yaml("[jupyter]"),
        )
        expected_repo["hooks"].append(black_jupyter)
    precommit.update_single_hook_repo(expected_repo)
