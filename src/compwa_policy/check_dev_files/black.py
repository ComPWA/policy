"""Update :file:`pyproject.toml` black configuration."""

from ruamel.yaml import YAML

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    remove_precommit_hook,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.project_info import get_supported_python_versions
from compwa_policy.utilities.pyproject import (
    complies_with_subset,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)


def main(has_notebooks: bool) -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    executor = Executor()
    executor(_remove_outdated_settings)
    executor(_update_black_settings)
    executor(
        remove_precommit_hook,
        hook_id="black",
        repo_url="https://github.com/psf/black",
    )
    executor(
        remove_precommit_hook,
        hook_id="black-jupyter",
        repo_url="https://github.com/psf/black",
    )
    executor(_update_precommit_repo, has_notebooks)
    executor(vscode.add_extension_recommendation, "ms-python.black-formatter")
    executor(
        vscode.update_settings, {"black-formatter.importStrategy": "fromEnvironment"}
    )
    executor(
        vscode.update_settings,
        {
            "[python]": {
                "editor.defaultFormatter": "ms-python.black-formatter",
                "editor.rulers": [88],
            },
        },
    )
    executor(remove_precommit_hook, "nbqa-black")
    executor.finalize()


def _remove_outdated_settings() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.black", create=True)
    forbidden_options = ("line-length",)
    removed_options = set()
    for option in forbidden_options:
        if option in settings:
            removed_options.add(option)
            settings.remove(option)
    if removed_options:
        write_pyproject(pyproject)
        msg = (
            f"Removed {', '.join(sorted(removed_options))} option from black"
            f" configuration in {CONFIG_PATH.pyproject}"
        )
        raise PrecommitError(msg)


def _update_black_settings() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.black", create=True)
    versions = get_supported_python_versions()
    target_version = to_toml_array(sorted("py" + v.replace(".", "") for v in versions))
    minimal_settings = {
        "preview": True,
        "target-version": target_version,
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated black configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


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
