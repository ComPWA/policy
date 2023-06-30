"""Remove `isort <https://pycqa.github.io/isort>`_ and its configuration."""

from typing import TYPE_CHECKING

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    find_repo,
    load_round_trip_precommit_config,
    remove_precommit_hook,
)
from repoma.utilities.pyproject import load_pyproject, write_pyproject
from repoma.utilities.readme import remove_badge
from repoma.utilities.vscode import (
    add_unwanted_extension,
    remove_extension_recommendation,
    remove_settings,
)

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedSeq


def main() -> None:
    executor = Executor()
    executor(_check_pyproject)
    executor(_remove_precommit_hook)
    executor(add_unwanted_extension, "ms-python.isort")
    executor(remove_extension_recommendation, "ms-python.isort")
    executor(remove_precommit_hook, "isort")
    executor(remove_precommit_hook, "nbqa-isort")
    executor(remove_settings, ["isort.check", "isort.importStrategy"])
    executor(remove_badge, r".*https://img\.shields\.io/badge/%20imports\-isort")
    executor.finalize()


def _check_pyproject() -> None:
    pyproject = load_pyproject()
    if pyproject.get("tool", {}).get("isort") is None:
        return
    pyproject["tool"].remove("isort")  # type: ignore[union-attr]
    write_pyproject(pyproject)
    msg = f"Removed [tool.isort] section from {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _remove_precommit_hook() -> None:
    config, yaml = load_round_trip_precommit_config()
    idx_and_repo = find_repo(config, r"https://github.com/pycqa/isort")
    if idx_and_repo is None:
        return
    repos: CommentedSeq = config["repos"]
    idx, _ = idx_and_repo
    repos.pop(idx)
    yaml.dump(config, CONFIG_PATH.precommit)
    msg = "Removed pre-commit hook for isort"
    raise PrecommitError(msg)
