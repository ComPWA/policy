"""Update `uv <https://docs.astral.sh/uv>`_ configuration."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import rtoml
from jinja2 import Environment, FileSystemLoader

from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, readme, vscode
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject.getters import has_sub_table

if TYPE_CHECKING:
    from compwa_policy.env.conda import PackageManagerChoice
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.pyproject import ModifiablePyproject
    from compwa_policy.utilities.pyproject.getters import PythonVersion
    from compwa_policy.utilities.session import Changelog, Session


def main(  # noqa: PLR0917
    session: Session,
    dev_python_version: PythonVersion,
    keep_contributing_md: bool,
    package_manager: PackageManagerChoice,
    organization: str,
    repo_name: str,
) -> None:
    precommit_config = session.precommit
    if "uv" in package_manager:
        readme.add_badge(
            session,
            "[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)",
        )
        session.changelog += _update_editor_config()
        _update_python_version_file(session, dev_python_version)
        _update_uv_lock_hook(precommit_config)
        if not keep_contributing_md:
            _update_contributing_file(session, organization, repo_name)
        session.changelog += _remove_pip_constraint_files()
        vscode.remove_settings(
            session,
            {"files.associations": ["**/.constraints/py*.txt"]},
        )
        vscode.remove_settings(
            session,
            {
                "search.exclude": [
                    "**/.constraints/py*.txt",
                    ".constraints/*.txt",
                ]
            },
        )
    else:
        _remove_uv_configuration(session.pyproject)
        session.changelog += _remove_uv_lock()
        precommit_config.remove_hook("uv-lock")
        readme.remove_badge(
            session,
            r"\[\!\[[^\[]+\]\(https://img\.shields\.io/[^\)]+/uv/main/assets/badge/[^\)]+\)\]\(https://github\.com/astral-sh/uv\)",
        )
        vscode.remove_settings(session, {"search.exclude": ["uv.lock", "**/uv.lock"]})


def _remove_pip_constraint_files() -> Changelog:
    if not CONFIG_PATH.pip_constraints.exists():
        return []
    for item in CONFIG_PATH.pip_constraints.iterdir():
        if item.is_dir():
            item.rmdir()
        else:
            item.unlink()
    CONFIG_PATH.pip_constraints.rmdir()
    msg = f"Removed deprecated {CONFIG_PATH.pip_constraints}. Use uv.lock instead."
    return [msg]


def _remove_uv_configuration(pyproject: ModifiablePyproject | None) -> None:
    if pyproject is None:
        return
    readonly_pyproject = pyproject._document  # noqa: SLF001
    if "tool" not in readonly_pyproject or "uv" not in readonly_pyproject["tool"]:
        return
    tool_table = pyproject.get_table("tool")
    tool_table.pop("uv")
    pyproject.changelog.append("Removed uv configuration from pyproject.toml.")


def _remove_uv_lock() -> Changelog:
    uv_lock_path = Path("uv.lock")
    if uv_lock_path.exists():
        uv_lock_path.unlink()
        msg = f"Removed {uv_lock_path} file."
        return [msg]
    return []


def _update_editor_config() -> Changelog:
    if not CONFIG_PATH.editorconfig.exists():
        return []
    if not is_committed("uv.lock"):
        return []
    expected_content = dedent("""
    [uv.lock]
    indent_size = 4
    """).strip()
    existing_content = CONFIG_PATH.editorconfig.read_text()
    if expected_content in existing_content:
        return []
    with open(CONFIG_PATH.editorconfig, "a") as stream:
        stream.write("\n" + expected_content + "\n")
    return [f"Updated {CONFIG_PATH.editorconfig} for uv.lock"]


def _update_python_version_file(
    session: Session,
    /,
    dev_python_version: PythonVersion,
) -> None:
    pyproject = session.pyproject
    if pyproject is None:
        return
    python_version_file = Path(".python-version")
    if pyproject.has_table("project"):
        requires_python = pyproject.get_table("project").get("requires-python", "")
        if "==" in requires_python or "~=" in requires_python:
            if python_version_file.exists():
                python_version_file.unlink()
                msg = f"Removed {python_version_file} file because requires-python already pins the Python version"
                session.changelog.append(msg)
                return
            return

    existing_python_version = ""
    if python_version_file.exists():
        with open(python_version_file) as stream:
            existing_python_version = stream.read().strip()
    if existing_python_version == dev_python_version:
        return
    with open(".python-version", "w") as stream:
        stream.write(dev_python_version + "\n")
    msg = f"Updated {python_version_file} to {dev_python_version}"
    session.changelog.append(msg)


def _update_uv_lock_hook(precommit: ModifiablePrecommit) -> None:
    if is_committed("uv.lock"):
        repo = Repo(
            repo="https://github.com/astral-sh/uv-pre-commit",
            rev="0.4.20",
            hooks=[Hook(id="uv-lock")],
        )
        precommit.update_single_hook_repo(repo)
    else:
        precommit.remove_hook("uv-lock")


def _update_contributing_file(
    session: Session,
    /,
    organization: str,
    repo_name: str,
) -> None:
    contributing_file = Path("CONTRIBUTING.md")
    if not contributing_file.exists():
        return
    template_dir = COMPWA_POLICY_DIR / ".template"
    env = Environment(
        autoescape=True,
        loader=FileSystemLoader(template_dir),
    )
    template = env.get_template("CONTRIBUTING.md.jinja")
    context = {
        "ORGANIZATION": organization,
        "REPO_NAME": repo_name,
        "RUNNER": __get_runner_instructions(session).strip(),
    }
    expected_content = template.render(context).strip() + "\n"
    existing_content = ""
    if contributing_file.exists():
        existing_content = contributing_file.read_text()
    if expected_content != existing_content:
        contributing_file.write_text(expected_content)
        msg = f"Updated {contributing_file} to latest template"
        session.changelog.append(msg)


def __get_runner_instructions(session: Session, /) -> str:
    poe_instructions = dedent("""
    [Poe the Poet](https://poethepoet.natn.io) is used as a task runner. Install it globally (within your home folder) with `uv`:

    ```shell
    uv tool install poethepoet --force-reinstall --python=3.13
    ```

    You can see which local CI checks it defines by running

    ```shell
    poe
    ```

    For instance, all style checks can be run with

    ```shell
    poe style
    ```
    """)
    pixi_instructions = dedent("""
    Pixi is used as a [task runner](https://pixi.sh/latest/workspace/advanced_tasks). You can see which local CI checks it defines by running

    ```shell
    pixi task list
    ```

    For instance, all style checks can be run with

    ```shell
    pixi run style
    ```
    """)
    pyproject = session.pyproject
    if pyproject is not None:
        if pyproject.has_table("tool.poe.tasks"):
            return poe_instructions
        if pyproject.has_table("tool.pixi.tasks"):
            return pixi_instructions
    if CONFIG_PATH.pixi_toml.exists():
        pixi_config = rtoml.load(CONFIG_PATH.pixi_toml)
        if has_sub_table(pixi_config, "tasks"):
            return pixi_instructions
    return ""
