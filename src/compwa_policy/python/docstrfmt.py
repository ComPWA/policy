"""Install `docstrfmt <https://github.com/LilSpazJoekp/docstrfmt>`_ as a hook."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.precommit.struct import Hook, Repo

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.pyproject import ModifiablePyproject
    from compwa_policy.utilities.session import Session

__DEFAULT_SETTINGS = {
    "docstring-trailing-line": False,
    "format-python-code-blocks": False,
}
"""Settings that match Ruff, which already formats code in docstrings."""


@check_hook(
    group="python",
    paths=[CONFIG_PATH.precommit, CONFIG_PATH.pyproject],
    enabled=lambda _args, ctx: ctx.is_python_repo,
)
def check(session: Session, args: Arguments, _: CheckContext) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if args.docstrfmt:
        precommit.update_single_hook_repo(
            Repo(
                repo="https://github.com/LilSpazJoekp/docstrfmt",
                rev="",
                hooks=[Hook(id="docstrfmt")],
            )
        )
        if pyproject is not None:
            _update_settings(pyproject)
    else:
        precommit.remove_hook("docstrfmt")
        if pyproject is not None and pyproject.has_table("tool.docstrfmt"):
            del pyproject._document["tool"]["docstrfmt"]  # ruff: ignore[private-member-access]
            pyproject.changelog.append("Removed docstrfmt configuration table")


def _update_settings(pyproject: ModifiablePyproject) -> None:
    settings = pyproject.get_table("tool.docstrfmt", create=True)
    for key, value in __DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
            pyproject.changelog.append(f"Set tool.docstrfmt.{key} = {value}")
