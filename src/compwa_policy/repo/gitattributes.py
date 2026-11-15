"""Normalize line endings through :file:`.gitattributes`.

Each repository configures EditorConfig to expect LF line endings. On Windows, Git
checks files out with CRLF line endings if ``core.autocrlf`` is set, so checks like
``editorconfig-checker`` fail on files that were never touched. The attribute ``*
text=auto eol=lf`` makes Git check out text files with LF line endings, regardless of
the configuration of the user.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Session

EXPECTED_LINE = "* text=auto eol=lf"
"""Catch-all attribute that has to come first, so that later patterns override it."""


@check_hook(group="repo", paths=[CONFIG_PATH.gitattributes])
def check(session: Session, _args: Arguments, _ctx: CheckContext) -> None:
    resource = session.get_path(CONFIG_PATH.gitattributes)
    content = resource.read_text() if resource.exists else ""
    if EXPECTED_LINE in {line.strip() for line in content.splitlines()}:
        return
    resource.write_text(
        f"{EXPECTED_LINE}\n{content}",
        f"Added '{EXPECTED_LINE}' to {CONFIG_PATH.gitattributes}",
    )
