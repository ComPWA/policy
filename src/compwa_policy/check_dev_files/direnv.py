"""Update the :file:`.envrc` file for `direnv <https://direnv.net/>`_."""

from __future__ import annotations

from textwrap import dedent

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject


def main() -> None:
    if (
        CONFIG_PATH.pixi_lock.exists()
        or CONFIG_PATH.pixi_toml.exists()
        or (CONFIG_PATH.pyproject.exists() and Pyproject.load().has_table("tool.pixi"))
    ):
        _update_envrc("""
        watch_file pixi.lock
        eval "$(pixi shell-hook)"
        """)
    elif CONFIG_PATH.conda.exists():
        _update_envrc("layout anaconda")


def _update_envrc(expected: str) -> None:
    expected = dedent(expected).strip() + "\n"
    existing = __get_existing_envrc()
    if existing == expected:
        return
    with open(".envrc", "w") as f:
        f.write(expected)
    msg = "Updated .envrc for direnv"
    raise PrecommitError(msg)


def __get_existing_envrc() -> str | None:
    if not CONFIG_PATH.envrc.exists():
        return None
    with open(CONFIG_PATH.envrc) as f:
        return f.read()
