"""Remove `flake8 <https://flake8.pycqa.org>`_ and its configuration."""

import os
from configparser import ConfigParser
from typing import Optional

from repoma.errors import PrecommitError
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import remove_precommit_hook
from repoma.utilities.setup_cfg import open_setup_cfg
from repoma.utilities.vscode import (
    add_unwanted_extension,
    remove_extension_recommendation,
)


def main() -> None:
    executor = Executor()
    executor(_remove_flake8_config)
    executor(_check_setup_cfg)
    executor(add_unwanted_extension, "ms-python.flake8")
    executor(remove_extension_recommendation, "ms-python.flake8")
    executor(remove_precommit_hook, "autoflake")  # cspell:ignore autoflake
    executor(remove_precommit_hook, "flake8")
    executor(remove_precommit_hook, "nbqa-flake8")
    executor.finalize()


def _remove_flake8_config() -> None:
    for config_file in [
        ".flake8",
    ]:
        if os.path.exists(config_file):
            os.remove(config_file)


def _check_setup_cfg(cfg: Optional[ConfigParser] = None) -> None:
    if cfg is None:
        cfg = open_setup_cfg()
    extras_require = "options.extras_require"
    if not cfg.has_section(extras_require):
        return
    if not cfg.has_option(extras_require, "flake8"):
        return
    msg = f"""
    Please remove the flake section from the {extras_require!r} section of {cfg!r}
    """
    raise PrecommitError(msg.strip())
