"""Update pixi implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.env.pixi._helpers import has_pixi_config
from compwa_policy.env.pixi._remove import remove_pixi_configuration
from compwa_policy.env.pixi._update import update_pixi_configuration
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.check_hook import check_hook

if TYPE_CHECKING:
    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Session

__all__ = [
    "check",
    "has_pixi_config",
]


@check_hook(
    group="env",
    paths=[
        CONFIG_PATH.conda,
        CONFIG_PATH.gitattributes,
        CONFIG_PATH.gitignore,
        CONFIG_PATH.pixi_lock,
        CONFIG_PATH.pixi_toml,
        CONFIG_PATH.pyproject,
        CONFIG_PATH.vscode_settings,
    ],
)
def check(session: Session, args: Arguments, ctx: CheckContext) -> None:
    if "pixi" in args.package_manager:
        update_pixi_configuration(
            session,
            ctx.is_python_repo,
            args.dev_python_version,
            args.package_manager,
        )
    else:
        remove_pixi_configuration(session)
