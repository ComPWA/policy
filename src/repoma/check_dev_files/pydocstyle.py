"""Remove `pydocstyle <https://pydocstyle.org>`_ and its configuration."""

import os

from repoma.errors import PrecommitError
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import remove_precommit_hook
from repoma.utilities.setup_cfg import open_setup_cfg
from repoma.utilities.vscode import set_setting


def main() -> None:
    executor = Executor()
    executor(_remove_pydocstyle_config)
    executor(_check_setup_cfg)
    executor(remove_precommit_hook, "pydocstyle")
    executor(set_setting, {"python.linting.pydocstyleEnabled": False})
    executor.finalize()


def _remove_pydocstyle_config() -> None:
    executor = Executor()
    for config_file in [
        ".pydocstyle",
        "docs/.pydocstyle",
        "tests/.pydocstyle",
    ]:
        executor(__remove_path, config_file)
    executor.finalize()


def __remove_path(path: str) -> None:
    if not os.path.exists(path):
        return
    os.remove(path)
    msg = f"Removed {path}"
    raise PrecommitError(msg)


def _check_setup_cfg() -> None:
    cfg = open_setup_cfg()
    extras_require = "options.extras_require"
    if not cfg.has_section(extras_require):
        return
    for option in ["lint", "sty"]:
        if not cfg.has_option(extras_require, option):
            continue
        if "pydocstyle" not in cfg.get(extras_require, option):
            continue
        msg = (
            f'Please remove pydocstyle from the "{extras_require}" section of setup.cfg'
        )
        raise PrecommitError(msg)
