"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq

from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    remove_precommit_hook,
    update_precommit_hook,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.pyproject import PyprojectTOML


def main(no_ruff: bool) -> None:
    with Executor() as do:
        if no_ruff:
            do(_update_precommit_repo)
            do(_update_precommit_nbqa_hook)
        else:
            do(_remove_pyupgrade)


def _update_precommit_repo() -> None:
    expected_hook = Repo(
        repo="https://github.com/asottile/pyupgrade",
        rev="",
        hooks=[
            Hook(
                id="pyupgrade",
                args=__get_pyupgrade_version_argument(),
            )
        ],
    )
    update_single_hook_precommit_repo(expected_hook)


def _update_precommit_nbqa_hook() -> None:
    update_precommit_hook(
        repo_url="https://github.com/nbQA-dev/nbQA",
        expected_hook=Hook(
            id="nbqa-pyupgrade",
            args=__get_pyupgrade_version_argument(),
        ),
    )


def __get_pyupgrade_version_argument() -> CommentedSeq:
    """Get the --py3x-plus argument for pyupgrade.

    >>> __get_pyupgrade_version_argument()
    ['--py37-plus']
    """
    supported_python_versions = PyprojectTOML.load().get_supported_python_versions()
    lowest_version = supported_python_versions[0]
    version_repr = lowest_version.replace(".", "")
    yaml = YAML(typ="rt")
    return yaml.load(f"[--py{version_repr}-plus]")


def _remove_pyupgrade() -> None:
    with Executor() as do:
        do(remove_precommit_hook, "nbqa-pyupgrade")
        do(remove_precommit_hook, "pyupgrade")
