"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""

from repoma._utilities import (
    CONFIG_PATH,
    find_hook_index,
    get_prettier_round_trip_yaml,
)
from repoma.pre_commit_hooks.errors import PrecommitError

__PYUPGRADE_URL = "https://github.com/asottile/pyupgrade"
__EXPECTED_ARGS = [
    "--py36-plus",
]


def check_pyupgrade_hook() -> None:
    yaml = get_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.pre_commit)
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
