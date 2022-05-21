"""Check :file:`pyproject.toml` black config."""

from collections import OrderedDict
from textwrap import dedent
from typing import Optional

import toml

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, natural_sorting
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    PrecommitConfig,
    load_round_trip_precommit_config,
)
from repoma.utilities.setup_cfg import get_supported_python_versions


def main() -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    config = _load_config()
    executor = Executor()
    executor(_check_line_length, config)
    executor(_check_activate_preview, config)
    executor(_check_option_ordering, config)
    executor(_check_target_versions, config)
    executor(_update_nbqa_hook)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _load_config(content: Optional[str] = None) -> dict:
    if content is None:
        with open(CONFIG_PATH.pyproject) as stream:
            config = toml.load(stream, _dict=OrderedDict)
    else:
        config = toml.loads(content, _dict=OrderedDict)
    return config.get("tool", {}).get("black")


def _check_activate_preview(config: dict) -> None:
    expected_option = "preview"
    if config.get(expected_option) is not True:
        raise PrecommitError(
            dedent(
                f"""
            An option in pyproject.toml is wrong or missing. Should be:

            [tool.black]
            {expected_option} = true
            """
            ).strip()
        )


def _check_line_length(config: dict) -> None:
    expected_line_length = 79
    if config.get("line-length") != expected_line_length:
        raise PrecommitError(
            dedent(
                f"""
            Black line-length in pyproject.toml in pyproject.toml should be:

            [tool.black]
            line-length = {expected_line_length}
            """
            ).strip()
        )


def _check_option_ordering(config: dict) -> None:
    options = list(config)
    sorted_options = sorted(config, key=natural_sorting)
    if sorted_options != options:
        error_message = dedent(
            """
            Options in pyproject.toml should be alphabetically sorted:

            [tool.black]
            """
        ).strip()
        for option in sorted_options:
            error_message += f"\n{option} = ..."
        raise PrecommitError(error_message)


def _check_target_versions(config: dict) -> None:
    target_versions = config.get("target-version", [])
    supported_python_versions = get_supported_python_versions()
    expected_target_versions = sorted(
        ("py" + s.replace(".", "") for s in supported_python_versions),
        key=natural_sorting,
    )
    if target_versions != expected_target_versions:
        error_message = dedent(
            """
            Black target versions in pyproject.toml should be as follows:

            [tool.black]
            target-version = [
            """
        ).strip()
        for version in expected_target_versions:
            error_message += f"\n    '{version}',"
        error_message += "\n]"
        raise PrecommitError(error_message)


def _update_nbqa_hook() -> None:
    repo_url = "https://github.com/nbQA-dev/nbQA"
    precommit_config = PrecommitConfig.load()
    repo = precommit_config.find_repo(repo_url)
    if repo is None:
        return

    hook_id = "nbqa-black"
    expected_config = {
        "id": hook_id,
        "additional_dependencies": [
            "black>=22.1.0",
        ],
    }
    repo_index = precommit_config.get_repo_index(repo_url)
    hook_index = repo.get_hook_index(hook_id)
    if hook_index is None:
        config, yaml = load_round_trip_precommit_config()
        config["repos"][repo_index]["hooks"].append(expected_config)
        yaml.dump(config, CONFIG_PATH.precommit)
        raise PrecommitError(f"Added {hook_id} to pre-commit config")

    if repo.hooks[hook_index].dict(skip_defaults=True) != expected_config:
        config, yaml = load_round_trip_precommit_config()
        config["repos"][repo_index]["hooks"][hook_index] = expected_config
        yaml.dump(config, CONFIG_PATH.precommit)
        raise PrecommitError(f"Updated args of {hook_id} pre-commit hook")
