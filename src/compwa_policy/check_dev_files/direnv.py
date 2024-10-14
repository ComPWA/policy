"""Update the :file:`.envrc` file for `direnv <https://direnv.net/>`_."""

from __future__ import annotations

from textwrap import dedent, indent
from typing import TYPE_CHECKING

import rtoml

from compwa_policy.check_dev_files.pixi import has_pixi_config
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject

if TYPE_CHECKING:
    from compwa_policy.check_dev_files.conda import PackageManagerChoice


def main(package_manager: PackageManagerChoice, variables: dict[str, str]) -> None:
    if package_manager == "none":
        return
    if package_manager == "uv":
        _update_envrc_for_uv_only(variables)
    else:
        statements: list[tuple[str | None, str]] = [
            (".venv", "source .venv/bin/activate"),
            ("venv", "source venv/bin/activate"),
        ]
        if has_pixi_config():
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


def _update_envrc_for_uv_only(variables: dict[str, str]) -> None:
    expected = dedent(
        """
    uv sync --all-extras --quiet
    source .venv/bin/activate
    """
    ).strip()
    for name, value in variables.items():
        expected += f"\nexport {name}={value}"
    __update_envrc_content(expected + "\n")


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
    __update_envrc_content(expected)


def __update_envrc_content(expected: str) -> None:
    if __get_existing_envrc() == expected:
        return
    with open(CONFIG_PATH.envrc, "w") as f:
        f.write(expected)
    msg = f"Updated {CONFIG_PATH.envrc} for direnv"
    raise PrecommitError(msg)


def __get_existing_envrc() -> str | None:
    if not CONFIG_PATH.envrc.exists():
        return None
    with open(CONFIG_PATH.envrc) as f:
        return f.read()
