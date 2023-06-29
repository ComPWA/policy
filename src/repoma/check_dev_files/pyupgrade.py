"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""

from ruamel.yaml.comments import CommentedMap

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, natural_sorting
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    Hook,
    PrecommitConfig,
    asdict,
    load_round_trip_precommit_config,
    update_single_hook_precommit_repo,
)
from repoma.utilities.setup_cfg import get_supported_python_versions


def main() -> None:
    executor = Executor()
    executor(_update_precommit_repo)
    executor(_update_nbqa_hook)
    executor.finalize()


def _update_precommit_repo() -> None:
    expected_hook = CommentedMap(
        repo="https://github.com/asottile/pyupgrade",
        hooks=[
            CommentedMap(
                id="pyupgrade",
                args=[__get_pyupgrade_version_argument()],
            )
        ],
    )
    update_single_hook_precommit_repo(expected_hook)


def _update_nbqa_hook() -> None:
    repo_url = "https://github.com/nbQA-dev/nbQA"
    precommit_config = PrecommitConfig.load()
    repo = precommit_config.find_repo(repo_url)
    if repo is None:
        return

    hook_id = "nbqa-pyupgrade"
    expected = Hook(
        hook_id,
        args=[__get_pyupgrade_version_argument()],
    )
    repo_index = precommit_config.get_repo_index(repo_url)
    hook_index = repo.get_hook_index(hook_id)
    if hook_index is None:
        config, yaml = load_round_trip_precommit_config()
        config["repos"][repo_index]["hooks"].append(asdict(expected))
        yaml.dump(config, CONFIG_PATH.precommit)
        raise PrecommitError(f"Added {hook_id} to pre-commit config")

    if repo.hooks[hook_index] != expected:
        config, yaml = load_round_trip_precommit_config()
        config["repos"][repo_index]["hooks"][hook_index] = asdict(expected)
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
