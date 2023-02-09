"""Configuration for working with TOML files."""

import os
import shutil
from textwrap import dedent

from ruamel.yaml.comments import CommentedSeq

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import PrecommitConfig
from repoma.utilities.vscode import (
    add_vscode_extension_recommendation,
    remove_vscode_extension_recommendation,
)
from repoma.utilities.yaml import create_prettier_round_trip_yaml

__INCORRECT_TAPLO_CONFIG_PATHS = [
    "taplo.toml",
]
__TRIGGER_FILES = [
    ".taplo.toml",
    "pyproject.toml",
    *__INCORRECT_TAPLO_CONFIG_PATHS,
]


def main() -> None:
    if not any(os.path.exists(f) for f in __TRIGGER_FILES):
        return
    executor = Executor()
    executor(_rename_taplo_config)
    executor(_update_precommit_config)
    executor(_update_vscode_extensions)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _rename_taplo_config() -> None:
    correct_path = ".taplo.toml"
    for path in __INCORRECT_TAPLO_CONFIG_PATHS:
        if not os.path.exists(path):
            continue
        shutil.move(path, correct_path)
        raise PrecommitError(f"Renamed {path} to {correct_path}")


def _update_precommit_config() -> None:
    if not os.path.exists(CONFIG_PATH.precommit):
        return
    existing_config = PrecommitConfig.load()
    repo_url = "https://github.com/ComPWA/mirrors-taplo"
    if existing_config.find_repo(repo_url) is not None:
        return
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.precommit)
    hook_definition = {
        "repo": repo_url,
        "rev": "v0.8.0",
        "hooks": [{"id": "taplo"}],
    }
    repos: CommentedSeq = config["repos"]
    repos.append(hook_definition)
    repo_idx = len(repos) - 1
    repos.yaml_set_comment_before_after_key(repo_idx, before="\n")
    yaml.dump(config, CONFIG_PATH.precommit)
    # cspell:ignore taplo
    msg = f"""
    Added Taplo TOML formatter as a pre-commit hook. Please run

        pre-commit autoupdate --repo {repo_url}

    to update it to the latest version.
    """
    raise PrecommitError(dedent(msg).strip())


def _update_vscode_extensions() -> None:
    # cspell:ignore bungcip tamasfe
    executor = Executor()
    executor(add_vscode_extension_recommendation, "tamasfe.even-better-toml")
    executor(remove_vscode_extension_recommendation, "bungcip.better-toml")
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())
