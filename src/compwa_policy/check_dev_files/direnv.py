"""Update the :file:`.envrc` file for `direnv <https://direnv.net/>`_."""

from __future__ import annotations

from textwrap import dedent, indent

import rtoml

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject


def main() -> None:
    statements: list[tuple[str | None, str]] = [
        (".venv", "source .venv/bin/activate"),
        ("venv", "source venv/bin/activate"),
    ]
    if (
        CONFIG_PATH.pixi_lock.exists()
        or CONFIG_PATH.pixi_toml.exists()
        or (CONFIG_PATH.pyproject.exists() and Pyproject.load().has_table("tool.pixi"))
    ):
        dev_environment = __determine_pixi_dev_environment()
        if dev_environment is None:
            environment_flag = ""
        else:
            environment_flag = f" --environment {dev_environment}"
        script = f"""
            watch_file pixi.lock
            eval "$(pixi shell-hook{environment_flag})"
        """
        statements.append((".pixi", script))
    if CONFIG_PATH.conda.exists():
        statements.append((None, "layout anaconda"))
    _update_envrc(statements)


def __determine_pixi_dev_environment() -> str | None:
    search_terms = ["dev"]
    if CONFIG_PATH.pyproject.exists():
        pyproject = Pyproject.load()
        package_name = pyproject.get_package_name()
        if package_name is not None:
            search_terms.append(package_name)
    available_environments = __get_pixi_environment_names()
    for candidate in search_terms:
        if candidate in available_environments:
            return candidate
    return None


def __get_pixi_environment_names() -> set[str]:
    if CONFIG_PATH.pixi_toml.exists():
        pixi_config = rtoml.load(CONFIG_PATH.pixi_toml)
        return set(pixi_config.get("environments", set()))
    if CONFIG_PATH.pyproject.exists():
        pyproject = Pyproject.load()
        if pyproject.has_table("tool.pixi.environments"):
            return set(pyproject.get_table("tool.pixi.environments"))
    return set()


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
