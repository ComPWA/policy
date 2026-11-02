"""Keep an existing `docstrfmt <https://github.com/LilSpazJoekp/docstrfmt>`_ hook consistent.

The hook is never added: docstrfmt assumes reStructuredText docstrings, so repositories
opt in by listing it in their pre-commit config.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Session

__FILE_TYPE_OVERRIDES = ("files", "types", "types_or")


@check_hook(
    group="python",
    paths=[CONFIG_PATH.precommit],
    enabled=lambda _args, ctx: ctx.is_python_repo,
)
def check(session: Session, _args: Arguments, _: CheckContext) -> None:
    """Let the upstream ``types_or: [python, rst]`` filter decide which files to format."""
    precommit = session.precommit
    repo = precommit.find_repo(r"^https://github\.com/LilSpazJoekp/docstrfmt$")
    if repo is None:
        return
    for hook in repo.get("hooks", []):
        if hook.get("id") != "docstrfmt":
            continue
        removed = [
            key for key in __FILE_TYPE_OVERRIDES if hook.pop(key, None) is not None
        ]
        if removed:
            keys = ", ".join(f"`{key}`" for key in removed)
            msg = f"Removed {keys} from docstrfmt hook in {CONFIG_PATH.precommit}"
            precommit.changelog.append(msg)
