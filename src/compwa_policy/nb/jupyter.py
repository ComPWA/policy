"""Update the developer setup when using Jupyter notebooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import vscode
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    use_modifiable_pyproject,
)

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Changelog, Session


def main(session: Session, no_ruff: bool) -> None:
    session.changelog += _update_dev_requirements(no_ruff, session.pyproject)
    # cspell:ignore toolsai
    session.changelog += vscode.add_extension_recommendation("ms-toolsai.jupyter")
    session.changelog += vscode.add_extension_recommendation(
        "ms-toolsai.vscode-jupyter-cell-tags"
    )
    session.changelog += vscode.remove_extension_recommendation(
        "ms-toolsai.vscode-jupyter-slideshow",
        unwanted=True,
    )


def _update_dev_requirements(
    no_ruff: bool,
    pyproject: ModifiablePyproject | None = None,
) -> Changelog:
    with use_modifiable_pyproject(pyproject) as (config, include_changelog):
        if config is None:
            return []
        supported_python_versions = config.get_supported_python_versions()
        if "3.6" in supported_python_versions:
            return []
        packages = {
            "jupyterlab",
            "jupyterlab-git",
            "jupyterlab-lsp",
            "jupyterlab-quickopen",  # cspell:ignore quickopen
            "python-lsp-server",
        }
        # cspell:ignore executablebookproject
        recommended_vscode_extensions = vscode.get_recommended_extensions()
        if "executablebookproject.myst-highlight" in recommended_vscode_extensions:
            packages.add("jupyterlab-myst")
        else:
            config.remove_dependency("jupyterlab-myst")
        if "quarto.quarto" in recommended_vscode_extensions:
            packages.add("jupyterlab-quarto")
        else:
            config.remove_dependency("jupyterlab-quarto")
        config.remove_dependency("python-lsp-server[rope]")
        if not no_ruff:
            config.remove_dependency(
                "black", ignored_sections=["doc", "notebooks", "test"]
            )
            config.remove_dependency("isort")
            config.remove_dependency("jupyterlab-code-formatter")
            packages.add("jupyter-ruff")
        for package in sorted(packages):
            config.add_dependency(package, dependency_group=["jupyter", "dev"])
        if include_changelog:
            return list(config.changelog)
    return []
