"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import Pyproject
from compwa_policy.utilities.yaml import read_preserved_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedSeq

    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.session import Session


def main(session: Session, no_ruff: bool) -> None:
    precommit = session.precommit
    if no_ruff:
        _update_precommit_repo(precommit)
        _update_precommit_nbqa_hook(precommit)
    else:
        _remove_pyupgrade(precommit)


def _update_precommit_repo(precommit: ModifiablePrecommit) -> None:
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
    precommit.update_single_hook_repo(expected_hook)


def _update_precommit_nbqa_hook(precommit: ModifiablePrecommit) -> None:
    precommit.update_hook(
        repo_url="https://github.com/nbQA-dev/nbQA",
        expected_hook=Hook(
            id="nbqa-pyupgrade",
            args=__get_pyupgrade_version_argument(),
        ),
    )


def __get_pyupgrade_version_argument() -> CommentedSeq:
    """Get the --py3x-plus argument for pyupgrade.

    >>> __get_pyupgrade_version_argument()
    ['--py310-plus']
    """
    supported_python_versions = Pyproject.load().get_supported_python_versions()
    lowest_version = supported_python_versions[0]
    version_repr = lowest_version.replace(".", "")
    return read_preserved_yaml(f"[--py{version_repr}-plus]")


def _remove_pyupgrade(precommit: ModifiablePrecommit) -> None:
    precommit.remove_hook("nbqa-pyupgrade")
    precommit.remove_hook("pyupgrade")
