"""Update :file:`pyproject.toml` black configuration."""

from ruamel.yaml.comments import CommentedMap

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    remove_precommit_hook,
    update_single_hook_precommit_repo,
)
from repoma.utilities.project_info import get_supported_python_versions
from repoma.utilities.pyproject import (
    complies_with_subset,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)
from repoma.utilities.vscode import (
    add_extension_recommendation,
    set_setting,
    set_sub_setting,
)


def main(has_notebooks: bool) -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    executor = Executor()
    executor(_remove_outdated_settings)
    executor(_update_black_settings)
    executor(_update_precommit_repo, has_notebooks)
    executor(add_extension_recommendation, "ms-python.black-formatter")
    executor(set_setting, {"black-formatter.importStrategy": "fromEnvironment"})
    executor(
        set_sub_setting,
        "[python]",
        {"editor.defaultFormatter": "ms-python.black-formatter"},
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
    expected_hook = CommentedMap(
        repo="https://github.com/psf/black",
        hooks=[CommentedMap(id="black")],
    )
    if has_notebooks:
        black_jupyter = CommentedMap(
            id="black-jupyter",
            args=["--line-length=85"],
            types_or=["jupyter"],
        )
        expected_hook["hooks"].append(black_jupyter)
    update_single_hook_precommit_repo(expected_hook)
