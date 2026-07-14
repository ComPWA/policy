"""Install `pyupgrade <https://github.com/asottile/pyupgrade>`_ as a hook."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.yaml import read_preserved_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedSeq

    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.session import Session


@check_hook(
    group="python",
    paths=[CONFIG_PATH.precommit, CONFIG_PATH.pyproject],
    enabled=lambda _args, ctx: ctx.is_python_repo,
)
def check(session: Session, args: Arguments, _: CheckContext) -> None:
    precommit = session.precommit
    if args.no_ruff:
        _update_precommit_repo(session)
        _update_precommit_nbqa_hook(session)
    else:
        _remove_pyupgrade(precommit)


def _update_precommit_repo(session: Session, /) -> None:
    precommit = session.precommit
    expected_hook = Repo(
        repo="https://github.com/asottile/pyupgrade",
        rev="",
        hooks=[
            Hook(
                id="pyupgrade",
                args=__get_pyupgrade_version_argument(session),
            )
        ],
    )
    precommit.update_single_hook_repo(expected_hook)


def _update_precommit_nbqa_hook(session: Session, /) -> None:
    precommit = session.precommit
    precommit.update_hook(
        repo_url="https://github.com/nbQA-dev/nbQA",
        expected_hook=Hook(
            id="nbqa-pyupgrade",
            args=__get_pyupgrade_version_argument(session),
        ),
    )


def __get_pyupgrade_version_argument(session: Session, /) -> CommentedSeq:
    """Get the --py3x-plus argument for pyupgrade.

    >>> from compwa_policy.utilities.session import Session
    >>> with Session() as session:
    ...     __get_pyupgrade_version_argument(session)
    ['--py310-plus']
    """
    pyproject = session.pyproject
    if pyproject is None:
        msg = "Cannot determine pyupgrade target without pyproject.toml"
        raise ValueError(msg)
    supported_python_versions = pyproject.get_supported_python_versions()
    lowest_version = supported_python_versions[0]
    version_repr = lowest_version.replace(".", "")
    return read_preserved_yaml(f"[--py{version_repr}-plus]")


def _remove_pyupgrade(precommit: ModifiablePrecommit) -> None:
    precommit.remove_hook("nbqa-pyupgrade")
    precommit.remove_hook("pyupgrade")
