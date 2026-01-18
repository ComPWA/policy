"""Update the developer setup when using Jupyter notebooks."""

from compwa_policy.utilities import vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    has_pyproject_package_name,
)


def main(no_ruff: bool) -> None:
    with Executor() as do:
        do(_update_dev_requirements, no_ruff)
        # cspell:ignore toolsai
        do(vscode.add_extension_recommendation, "ms-toolsai.jupyter")
        do(vscode.add_extension_recommendation, "ms-toolsai.vscode-jupyter-cell-tags")
        do(
            vscode.remove_extension_recommendation,
            "ms-toolsai.vscode-jupyter-slideshow",
            unwanted=True,
        )


def _update_dev_requirements(no_ruff: bool) -> None:
    if not has_pyproject_package_name():
        return
    with ModifiablePyproject.load() as pyproject:
        supported_python_versions = pyproject.get_supported_python_versions()
        if "3.6" in supported_python_versions:
            return
        packages = {
            "jupyterlab",
            "jupyterlab-git",
            "jupyterlab-lsp",
            "jupyterlab-myst",
            "jupyterlab-quickopen",  # cspell:ignore quickopen
            "python-lsp-server",
        }
        # cspell:ignore executablebookproject
        recommended_vscode_extensions = vscode.get_recommended_extensions()
        if "executablebookproject.myst-highlight" in recommended_vscode_extensions:
            packages.add("jupyterlab-myst")
        if "quarto.quarto" in recommended_vscode_extensions:
            packages.add("quarto-jupyter")
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
