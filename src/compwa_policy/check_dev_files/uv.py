"""Update `uv <https://docs.astral.sh/uv>`_ configuration."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import filter_files
from compwa_policy.utilities.precommit.struct import Hook, Repo

if TYPE_CHECKING:
    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.pyproject.getters import PythonVersion


def main(
    dev_python_version: PythonVersion,
    package_managers: set[PackageManagerChoice],
    precommit_config: ModifiablePrecommit,
    repo_name: str,
) -> None:
    if "uv" in package_managers:
        with Executor() as do:
            do(_update_editor_config)
            do(_update_python_version_file, dev_python_version)
            do(_update_uv_lock_hook, precommit_config)
            if {"uv"} == package_managers:
                do(_update_contributing_file, repo_name)
                do(_remove_pip_constraint_files)
                do(
                    vscode.remove_settings,
                    {"files.associations": ["**/.constraints/py*.txt"]},
                )
                do(
                    vscode.remove_settings,
                    {
                        "search.exclude": [
                            "**/.constraints/py*.txt",
                            ".constraints/*.txt",
                        ]
                    },
                )


def _remove_pip_constraint_files() -> None:
    if not CONFIG_PATH.pip_constraints.exists():
        return
    for item in CONFIG_PATH.pip_constraints.iterdir():
        if item.is_dir():
            item.rmdir()
        else:
            item.unlink()
    CONFIG_PATH.pip_constraints.rmdir()
    msg = f"Removed deprecated {CONFIG_PATH.pip_constraints}. Use uv.lock instead."
    raise PrecommitError(msg)


def _update_editor_config() -> None:
    if not CONFIG_PATH.editorconfig.exists():
        return
    expected_content = dedent("""
    [uv.lock]
    indent_size = 4
    """).strip()
    existing_content = CONFIG_PATH.editorconfig.read_text()
    if expected_content in existing_content:
        return
    with open(CONFIG_PATH.editorconfig, "a") as stream:
        stream.write("\n" + expected_content + "\n")


def _update_python_version_file(dev_python_version: PythonVersion) -> None:
    python_version_file = Path(".python-version")
    existing_python_version = ""
    if python_version_file.exists():
        with open(python_version_file) as stream:
            existing_python_version = stream.read().strip()
    if existing_python_version == dev_python_version:
        return
    with open(".python-version", "w") as stream:
        stream.write(dev_python_version + "\n")
    msg = f"Updated {python_version_file} to {dev_python_version}"
    raise PrecommitError(msg)


def _update_uv_lock_hook(precommit: ModifiablePrecommit) -> None:
    if filter_files(["uv.lock"]):
        repo = Repo(
            repo="https://github.com/astral-sh/uv-pre-commit",
            rev="0.4.20",
            hooks=[Hook(id="uv-lock")],
        )
        precommit.update_single_hook_repo(repo)


def _update_contributing_file(repo_name: str) -> None:
    template_dir = COMPWA_POLICY_DIR / ".template"
    env = Environment(
        autoescape=True,
        loader=FileSystemLoader(template_dir),
    )
    template = env.get_template("CONTRIBUTING.md.jinja")
    context = {"REPO_NAME": repo_name}
    expected_content = template.render(context) + "\n"
    existing_content = ""
    contributing_file = Path("CONTRIBUTING.md")
    if contributing_file.exists():
        existing_content = contributing_file.read_text()
    if expected_content != existing_content:
        contributing_file.write_text(expected_content)
        msg = f"Updated {contributing_file} to latest template"
        raise PrecommitError(msg)
