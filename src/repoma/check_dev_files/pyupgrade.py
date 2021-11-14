"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""

from ruamel.yaml import YAML

from repoma._utilities import (
    CONFIG_PATH,
    find_hook_index,
    get_prettier_round_trip_yaml,
)
from repoma.errors import PrecommitError

__PYUPGRADE_URL = "https://github.com/asottile/pyupgrade"
__EXPECTED_ARGS = [
    "--py36-plus",
]


def update_pyupgrade_hook() -> None:
    yaml = get_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.pre_commit)
    _update_main_pyupgrade_hook(config, yaml)
    _update_nbqa_hook(config, yaml)


def _update_main_pyupgrade_hook(config: dict, yaml: YAML) -> None:
    hook_index = find_hook_index(config, __PYUPGRADE_URL)
    if hook_index is None:
        config["repos"].append(
            {
                "repo": __PYUPGRADE_URL,
                "rev": "v2.29.0",
                "hooks": [
                    {
                        "id": "pyupgrade",
                        "args": __EXPECTED_ARGS,
                    }
                ],
            }
        )
        yaml.dump(config, CONFIG_PATH.pre_commit)
        raise PrecommitError("Added pyupgrade pre-commit hook")
    if config["repos"][hook_index]["hooks"][0].get("args") == __EXPECTED_ARGS:
        return
    config["repos"][hook_index]["hooks"]["args"] = __EXPECTED_ARGS
    yaml.dump(config, CONFIG_PATH.pre_commit)
    raise PrecommitError("Updated args of pyupgrade pre-commit hook")


def _update_nbqa_hook(config: dict, yaml: YAML) -> None:
    nbqa_index = find_hook_index(config, "https://github.com/nbQA-dev/nbQA")
    if nbqa_index is None:
        return
    hooks = config["repos"][nbqa_index]["hooks"]
    pyupgrade_index = None
    for i, hook in enumerate(hooks):
        if hook.get("id") == "nbqa-pyupgrade":
            pyupgrade_index = i
    expected_config = {
        "id": "nbqa-pyupgrade",
        "args": [
            "--py36-plus",
        ],
    }
    if pyupgrade_index is None:
        config["repos"][nbqa_index]["hooks"].append(expected_config)
        yaml.dump(config, CONFIG_PATH.pre_commit)
        raise PrecommitError("Added nbqa-pyupgrade to pre-commit config")
    if (
        config["repos"][nbqa_index]["hooks"][pyupgrade_index]
        != expected_config
    ):
        config["repos"][nbqa_index]["hooks"][pyupgrade_index] = expected_config
        yaml.dump(config, CONFIG_PATH.pre_commit)
        raise PrecommitError("Updated args of pyupgrade pre-commit hook")
