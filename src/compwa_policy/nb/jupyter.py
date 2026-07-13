"""Update the developer setup when using Jupyter notebooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Changelog, Session


def main(session: Session, no_ruff: bool) -> None:
    session.changelog += _update_dev_requirements(
        no_ruff, session.pyproject, session=session
    )
    # cspell:ignore toolsai
    session.changelog += vscode.add_extension_recommendation(
        "ms-toolsai.jupyter", session=session
    )
    session.changelog += vscode.add_extension_recommendation(
        "ms-toolsai.vscode-jupyter-cell-tags", session=session
    )
    session.changelog += vscode.remove_extension_recommendation(
        "ms-toolsai.vscode-jupyter-slideshow",
        unwanted=True,
        session=session,
    )


def _update_dev_requirements(
    no_ruff: bool,
    pyproject: ModifiablePyproject | None = None,
    *,
    session: Session | None = None,
) -> Changelog:
    if pyproject is None:
        if not CONFIG_PATH.pyproject.exists():
            return []
        with ModifiablePyproject.load() as config:
            _update_dev_requirements(no_ruff, config)
            return list(config.changelog)
    supported_python_versions = pyproject.get_supported_python_versions()
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
    recommended_vscode_extensions = vscode.get_recommended_extensions(session=session)
    if "executablebookproject.myst-highlight" in recommended_vscode_extensions:
        packages.add("jupyterlab-myst")
    else:
        pyproject.remove_dependency("jupyterlab-myst")
    if "quarto.quarto" in recommended_vscode_extensions:
        packages.add("jupyterlab-quarto")
    else:
        pyproject.remove_dependency("jupyterlab-quarto")
    pyproject.remove_dependency("python-lsp-server[rope]")
    if not no_ruff:
        pyproject.remove_dependency(
            "black", ignored_sections=["doc", "notebooks", "test"]
        )
        pyproject.remove_dependency("isort")
        pyproject.remove_dependency("jupyterlab-code-formatter")
        packages.add("jupyter-ruff")
    for package in sorted(packages):
        pyproject.add_dependency(package, dependency_group=["jupyter", "dev"])
    return []
