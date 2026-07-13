"""Update the developer setup when using Jupyter notebooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.utilities import vscode

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Session


def main(session: Session, no_ruff: bool) -> None:
    _update_dev_requirements(session, no_ruff)
    # cspell:ignore toolsai
    vscode.add_extension_recommendation(session, "ms-toolsai.jupyter")
    vscode.add_extension_recommendation(session, "ms-toolsai.vscode-jupyter-cell-tags")
    vscode.remove_extension_recommendation(
        session,
        "ms-toolsai.vscode-jupyter-slideshow",
        unwanted=True,
    )


def _update_dev_requirements(session: Session, /, no_ruff: bool) -> None:
    pyproject = session.pyproject
    if pyproject is None:
        return
    supported_python_versions = pyproject.get_supported_python_versions()
    if "3.6" in supported_python_versions:
        return
    packages = {
        "jupyterlab",
        "jupyterlab-git",
        "jupyterlab-lsp",
        "jupyterlab-quickopen",  # cspell:ignore quickopen
        "python-lsp-server",
    }
    # cspell:ignore executablebookproject
    recommended_vscode_extensions = vscode.get_recommended_extensions(session)
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
