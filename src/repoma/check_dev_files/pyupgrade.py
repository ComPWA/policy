"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""


from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, natural_sorting
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import PrecommitConfig, load_round_trip_precommit_config
from repoma.utilities.setup_cfg import get_supported_python_versions


def main() -> None:
    executor = Executor()
    executor(_update_main_pyupgrade_hook)
    executor(_update_nbqa_hook)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _update_main_pyupgrade_hook() -> None:
    repo_url = "https://github.com/asottile/pyupgrade"
    hook_id = "pyupgrade"
    expected_args = [
        __get_pyupgrade_version_argument(),
    ]
    precommit_config = PrecommitConfig.load()
    repo = precommit_config.find_repo(repo_url)
    if repo is None:
        raise PrecommitError(f"{CONFIG_PATH.precommit} is missing a hook: {repo_url}")
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
        yaml.dump(config, CONFIG_PATH.precommit)
        raise PrecommitError(f"Added {hook_id} pre-commit hook")
    if repo.hooks[index].args == expected_args:
        return
    config, yaml = load_round_trip_precommit_config()
    config["repos"][index]["hooks"]["args"] = expected_args
    yaml.dump(config, CONFIG_PATH.precommit)
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
            __get_pyupgrade_version_argument(),
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


def __get_pyupgrade_version_argument() -> str:
    """Get the --py3x-plus argument for pyupgrade.

    >>> __get_pyupgrade_version_argument()
    '--py36-plus'
    """
    supported_python_versions = sorted(
        (v.replace(".", "") for v in get_supported_python_versions()),
        key=natural_sorting,
    )
    lowest_version = supported_python_versions[0]
    return f"--py{lowest_version}-plus"
