"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""

from typing import Tuple

from ruamel.yaml import YAML

from repoma._utilities import (
    CONFIG_PATH,
    PrecommitConfig,
    create_prettier_round_trip_yaml,
)
from repoma.errors import PrecommitError


def update_pyupgrade_hook() -> None:
    _update_main_pyupgrade_hook()
    _update_nbqa_hook()


def _update_main_pyupgrade_hook() -> None:
    repo_url = "https://github.com/asottile/pyupgrade"
    hook_id = "pyupgrade"
    expected_args = [
        "--py36-plus",
    ]
    precommit_config = PrecommitConfig.load()
    repo = precommit_config.find_repo(repo_url)
    if repo is None:
        raise PrecommitError(
            f"{CONFIG_PATH.pre_commit} is missing a hook: {repo_url}"
        )
    index = repo.get_hook_index(hook_id)
    if index is None:
        config, yaml = load_round_trip_precommit_config()
        config["repos"].append(
            {
                "repo": repo_url,
                "rev": "v2.29.0",
                "hooks": [
                    {
                        "id": hook_id,
                        "args": expected_args,
                    }
                ],
            }
        )
        yaml.dump(config, CONFIG_PATH.pre_commit)
        raise PrecommitError(f"Added {hook_id} pre-commit hook")
    if repo.hooks[index].args == expected_args:
        return
    config, yaml = load_round_trip_precommit_config()
    config["repos"][index]["hooks"]["args"] = expected_args
    yaml.dump(config, CONFIG_PATH.pre_commit)
    raise PrecommitError(f"Updated args of {hook_id} pre-commit hook")


def _update_nbqa_hook() -> None:
    repo_url = "https://github.com/nbQA-dev/nbQA"
    precommit_config = PrecommitConfig.load()
    repo = precommit_config.find_repo(repo_url)
    if repo is None:
        return

    hook_id = "nbqa-pyupgrade"
    expected_config = {
        "id": hook_id,
        "args": [
            "--py36-plus",
        ],
    }
    index = repo.get_hook_index(hook_id)
    if index is None:
        config, yaml = load_round_trip_precommit_config()
        config["repos"][index]["hooks"].append(expected_config)
        yaml.dump(config, CONFIG_PATH.pre_commit)
        raise PrecommitError(f"Added {hook_id} to pre-commit config")

    if repo.hooks[index].dict(skip_defaults=True) != expected_config:
        config, yaml = load_round_trip_precommit_config()
        config["repos"][index]["hooks"][hook_id] = expected_config
        yaml.dump(config, CONFIG_PATH.pre_commit)
        raise PrecommitError(f"Updated args of {hook_id} pre-commit hook")


def load_round_trip_precommit_config() -> Tuple[dict, YAML]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.pre_commit)
    return config, yaml
