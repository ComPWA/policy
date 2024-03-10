"""Update :file:`pyproject.toml` black configuration."""

from ruamel.yaml import YAML

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    remove_precommit_hook,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.pyproject import ModifiablePyproject, complies_with_subset
from compwa_policy.utilities.toml import to_toml_array


def main(has_notebooks: bool) -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_remove_outdated_settings, pyproject)
        do(_update_black_settings, pyproject)
        do(
            remove_precommit_hook,
            hook_id="black",
            repo_url="https://github.com/psf/black",
        )
        do(
            remove_precommit_hook,
            hook_id="black-jupyter",
            repo_url="https://github.com/psf/black",
        )
        do(_update_precommit_repo, has_notebooks)
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
        do(remove_precommit_hook, "nbqa-black")


def _remove_outdated_settings(pyproject: ModifiablePyproject) -> None:
    settings = pyproject.get_table("tool.black", create=True)
    forbidden_options = ("line-length",)
    removed_options = set()
    for option in forbidden_options:
        if option in settings:
            settings.pop(option)
            removed_options.add(option)
    if removed_options:
        msg = (
            f"Removed {', '.join(sorted(removed_options))} option from black"
            f" configuration in {CONFIG_PATH.pyproject}"
        )
        pyproject.append_to_changelog(msg)


def _update_black_settings(pyproject: ModifiablePyproject) -> None:
    settings = pyproject.get_table("tool.black", create=True)
    versions = pyproject.get_supported_python_versions()
    target_version = to_toml_array(sorted("py" + v.replace(".", "") for v in versions))
    minimal_settings = {
        "preview": True,
        "target-version": target_version,
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        msg = f"Updated black configuration in {CONFIG_PATH.pyproject}"
        pyproject.append_to_changelog(msg)


def _update_precommit_repo(has_notebooks: bool) -> None:
    expected_repo = Repo(
        repo="https://github.com/psf/black-pre-commit-mirror",
        rev="",
        hooks=[Hook(id="black")],
    )
    if has_notebooks:
        black_jupyter = Hook(
            id="black-jupyter",
            args=YAML(typ="rt").load("[--line-length=85]"),
            types_or=YAML(typ="rt").load("[jupyter]"),
        )
        expected_repo["hooks"].append(black_jupyter)
    update_single_hook_precommit_repo(expected_repo)
