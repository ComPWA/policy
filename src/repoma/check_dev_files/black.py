"""Update :file:`pyproject.toml` black configuration."""

from ruamel.yaml.comments import CommentedMap

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    find_repo,
    load_round_trip_precommit_config,
    update_precommit_hook,
    update_single_hook_precommit_repo,
)
from repoma.utilities.pyproject import (
    complies_with_subset,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)
from repoma.utilities.setup_cfg import get_supported_python_versions


def main() -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    executor = Executor()
    executor(_remove_outdated_settings)
    executor(_update_black_settings)
    executor(_update_nbqa_settings)
    executor(_update_precommit_repo)
    executor(_update_precommit_nbqa_hook)
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


def _update_precommit_repo() -> None:
    expected_hook = CommentedMap(
        repo="https://github.com/psf/black",
        hooks=[CommentedMap(id="black")],
    )
    update_single_hook_precommit_repo(expected_hook)


def _update_precommit_nbqa_hook() -> None:
    update_precommit_hook(
        repo_url="https://github.com/nbQA-dev/nbQA",
        expected_hook=CommentedMap(
            id="nbqa-black",
            additional_dependencies=["black>=22.1.0"],
        ),
    )


def _update_nbqa_settings() -> None:
    # cspell:ignore addopts
    if not CONFIG_PATH.precommit.exists():
        return
    if not __has_nbqa_precommit_repo():
        return
    pyproject = load_pyproject()
    nbqa_table = get_sub_table(pyproject, "tool.nbqa.addopts", create=True)
    expected = ["--line-length=85"]
    if nbqa_table.get("black") != expected:
        nbqa_table["black"] = expected
        write_pyproject(pyproject)
        msg = "Added nbQA configuration for black"
        raise PrecommitError(msg)


def __has_nbqa_precommit_repo() -> bool:
    config, _ = load_round_trip_precommit_config()
    nbqa_repo = find_repo(config, "https://github.com/nbQA-dev/nbQA")
    if nbqa_repo is None:
        return False
    return True
