"""Remove `pylint <https://pylint.org>`_ and its configuration."""
import os
from typing import List

from repoma.errors import PrecommitError
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    remove_precommit_hook,
)
from repoma.utilities.setup_cfg import open_setup_cfg
from repoma.utilities.vscode import (
    add_unwanted_extension,
    remove_extension_recommendation,
    remove_settings,
    set_setting,
)


def main() -> None:
    executor = Executor()
    executor(_remove_config, ".pylintrc")  # cspell:ignore pylintrc
    executor(_remove_extension, "ms-python.pylint")
    executor(_uninstall, "pylint", check_options=["lint", "sty"])
    executor(remove_precommit_hook, "pylint")
    executor(remove_precommit_hook, "nbqa-pylint")
    executor(remove_settings, ["pylint.importStrategy"])
    executor(set_setting, {"python.linting.pylintEnabled": False})
    executor.finalize()


def _remove_config(path: str) -> None:
    if not os.path.exists(path):
        return
    os.remove(path)
    msg = f"Removed {path}"
    raise PrecommitError(msg)


def _remove_extension(extension_id: str) -> None:
    executor = Executor()
    executor(remove_extension_recommendation, extension_id)
    executor(add_unwanted_extension, extension_id)
    executor.finalize()


def _uninstall(package: str, check_options: List[str]) -> None:
    cfg = open_setup_cfg()
    section = "options.extras_require"
    if not cfg.has_section(section):
        return
    for option in check_options:
        if not cfg.has_option(section, option):
            continue
        if package not in cfg.get(section, option):
            continue
        msg = f'Please remove {package} from the "{section}" section of setup.cfg'
        raise PrecommitError(msg)
