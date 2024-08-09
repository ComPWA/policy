"""Update the :file:`.envrc` file for `direnv <https://direnv.net/>`_."""

from __future__ import annotations

from textwrap import dedent, indent

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject
from compwa_policy.utilities.python import has_constraint_files

__DIRENV_SCRIPTS = {
    "conda": "layout anaconda",
    "pixi": """
        watch_file pixi.lock
        eval "$(pixi shell-hook)"
    """,
    "venv": "source venv/bin/activate",
    "uv-venv": "source .venv/bin/activate",
    "uv-venv-update": """
        uv pip sync .constraints/py$(python3 --version | awk '{print $2}' | awk -F. '{print $1"."$2}').txt --quiet
        uv pip install --editable '.[dev]' --quiet
    """,
}


def main() -> None:
    uv_venv = __DIRENV_SCRIPTS["uv-venv"]
    if has_constraint_files():
        uv_venv += "\n" + dedent(__DIRENV_SCRIPTS["uv-venv-update"])
    statements: list[tuple[str | None, str]] = [
        (".venv", uv_venv),
        ("venv", __DIRENV_SCRIPTS["venv"]),
    ]
    if (
        CONFIG_PATH.pixi_lock.exists()
        or CONFIG_PATH.pixi_toml.exists()
        or (CONFIG_PATH.pyproject.exists() and Pyproject.load().has_table("tool.pixi"))
    ):
        statements.append((".pixi", __DIRENV_SCRIPTS["pixi"]))
    if CONFIG_PATH.conda.exists():
        statements.append((None, __DIRENV_SCRIPTS["conda"]))
    _update_envrc(statements)


def _update_envrc(statements: list[tuple[str | None, str]]) -> None:
    expected = ""
    for i, (trigger_path, script) in enumerate(statements):
        if trigger_path is not None:
            if_or_elif = "if" if i == 0 else "elif"
            expected += f"{if_or_elif} [ -e {trigger_path} ]; then\n"
        else:
            expected += "else\n"
        script = dedent(script).strip()
        expected += indent(script, prefix="  ") + "\n"
    expected += "fi\n"
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
