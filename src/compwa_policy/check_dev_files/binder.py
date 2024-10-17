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
from compwa_policy.utilities.pyproject import Pyproject

if TYPE_CHECKING:
    from pathlib import Path

    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.utilities.pyproject import PythonVersion


def main(
    package_manager: PackageManagerChoice,
    python_version: PythonVersion,
    apt_packages: list[str],
) -> None:
    with Executor() as do:
        do(_update_apt_txt, apt_packages)
        do(_update_post_build, package_manager)
        do(_make_executable, CONFIG_PATH.binder / "postBuild")
        do(_update_runtime_txt, python_version)


def _update_apt_txt(apt_packages: list[str]) -> None:
    apt_txt = CONFIG_PATH.binder / "apt.txt"
    if not apt_packages:
        if apt_txt.exists():
            apt_txt.unlink()
            msg = f"Removed {apt_txt}, because --doc-apt-packages does not specify any packages."
            raise PrecommitError(msg)
        return
    apt_packages = sorted(set(apt_packages))
    __update_file(
        expected_content="\n".join(apt_packages) + "\n",
        path=apt_txt,
    )


def _update_post_build(package_manager: PackageManagerChoice) -> None:
    if package_manager == "pixi+uv":
        expected_content = __get_post_builder_for_pixi_with_uv()
    elif package_manager == "uv":
        expected_content = __get_post_builder_for_uv()
    else:
        msg = f"Package manager {package_manager} is not supported."
        raise NotImplementedError(msg)
    __update_file(
        expected_content.strip() + "\n",
        path=CONFIG_PATH.binder / "postBuild",
    )


def __get_post_builder_for_pixi_with_uv() -> str:
    expected_content = dedent("""
        #!/bin/bash
        set -ex
        curl -LsSf https://pixi.sh/install.sh | bash
        export PATH="$HOME/.pixi/bin:$PATH"

        pixi_packages="$(NO_COLOR= pixi list --explicit --no-install | awk 'NR > 1 {print $1}')"
        if [[ -n "$pixi_packages" ]]; then
          pixi global install $pixi_packages
        fi
        pixi clean cache --yes
    """).strip()
    expected_content += "\n"
    notebook_extras = __get_notebook_extras()
    if "uv.lock" in set(git_ls_files(untracked=True)):
        expected_content += "\nuv export \\"
        for extra in notebook_extras:
            expected_content += f"\n  --extra {extra} \\"
        expected_content += dedent(R"""
              > requirements.txt
            uv pip install \
              --requirement requirements.txt \
              --system
            uv cache clean
        """)
    else:
        package = "."
        if notebook_extras:
            package = f"'.[{','.join(notebook_extras)}]'"
        expected_content += dedent(Rf"""
            uv pip install \
              --editable {package} \
              --no-cache \
              --system
        """)
    return expected_content


def __get_post_builder_for_uv() -> str:
    expected_content = dedent("""
        #!/bin/bash
        set -ex
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
    """).strip()
    notebook_extras = __get_notebook_extras()
    if "uv.lock" in set(git_ls_files(untracked=True)):
        expected_content += "\nuv export \\"
        for extra in notebook_extras:
            expected_content += f"\n  --extra {extra} \\"
        expected_content += dedent(R"""
              > requirements.txt
            uv pip install \
              --requirement requirements.txt \
              --system
            uv cache clean
        """)
    else:
        package = "."
        if notebook_extras:
            package = f"'.[{','.join(notebook_extras)}]'"
        expected_content += dedent(Rf"""
            uv pip install \
              --editable {package} \
              --no-cache \
              --system
        """)
    return expected_content


def __get_notebook_extras() -> list[str]:
    if not CONFIG_PATH.pyproject.exists():
        return []
    pyproject = Pyproject.load()
    table_key = "project.optional-dependencies"
    if not pyproject.has_table(table_key):
        return []
    optional_dependencies = pyproject.get_table(table_key)
    allowed_sections = {"jupyter", "notebooks"}
    return sorted(allowed_sections & set(optional_dependencies))


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
