"""Remove :file:`commitlint.config.js` config file.

See https://github.com/ComPWA/policy/issues/177.
"""

from __future__ import annotations

import os
from textwrap import dedent
from typing import TYPE_CHECKING

from compwa_policy.utilities.check_hook import check_hook

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Session


@check_hook(group="repo", paths=["commitlint.config.js"])
def check(session: Session, _args: Arguments, _ctx: CheckContext) -> None:
    path = "commitlint.config.js"
    if not os.path.exists(path):
        return
    os.remove(path)
    msg = f"""
    Remove outdated {path}. Commitlint is now configured through
    https://github.com/ComPWA/commitlint-config.
    """
    session.changelog.append(dedent(msg).strip().replace("\n", " "))
