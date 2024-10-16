"""Add configuration for Binder.

See also https://mybinder.readthedocs.io/en/latest/using/config_files.html.
"""

from __future__ import annotations

import os
from textwrap import dedent
from typing import TYPE_CHECKING

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import git_ls_files

if TYPE_CHECKING:
    from pathlib import Path

    from compwa_policy.utilities.pyproject import PythonVersion


def main(python_version: PythonVersion, apt_packages: list[str]) -> None:
    with Executor() as do:
        do(_update_apt_txt, apt_packages)
        do(_update_post_build)
        do(_make_executable, CONFIG_PATH.binder / "postBuild")
        do(_update_runtime_txt, python_version)


def _update_apt_txt(apt_packages: list[str]) -> None:
    apt_txt = CONFIG_PATH.binder / "apt.txt"
    if not apt_packages and apt_txt.exists():
        apt_txt.unlink()
        msg = f"Removed {apt_txt}, because --doc-apt-packages does not specify any packages."
        raise PrecommitError(msg)
    apt_packages = sorted(set(apt_packages))
    __update_file(
        expected_content="\n".join(apt_packages) + "\n",
        path=apt_txt,
    )


def _update_post_build() -> None:
    expected_content = dedent("""
        #!/bin/bash
        set -ex
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
    """).strip()
    if "uv.lock" in set(git_ls_files(untracked=True)):
        expected_content += dedent(R"""
            uv export \
              --extra jupyter \
              --extra notebooks \
              > requirements.txt
            uv pip install \
              --requirement requirements.txt \
              --system
            uv cache clean
        """)
    else:
        expected_content += dedent(R"""
            uv pip install \
              --editable '.[jupyter,notebooks]' \
              --no-cache \
              --system
        """)
    __update_file(
        expected_content.strip() + "\n",
        path=CONFIG_PATH.binder / "postBuild",
    )


def _make_executable(path: Path) -> None:
    if os.access(path, os.X_OK):
        return
    msg = f"{path} has been made executable"
    path.chmod(0o755)
    raise PrecommitError(msg)


def _update_runtime_txt(python_version: PythonVersion) -> None:
    __update_file(
        expected_content=f"python-{python_version}\n",
        path=CONFIG_PATH.binder / "runtime.txt",
    )


def __update_file(expected_content: str, path: Path) -> None:
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        with open(path) as stream:
            if stream.read() == expected_content:
                return
    with open(path, "w") as stream:
        stream.write(expected_content)
    msg = f"Updated {path}"
    raise PrecommitError(msg)
