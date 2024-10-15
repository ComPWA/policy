"""Update the developer setup when using Jupyter notebooks."""

from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    has_pyproject_package_name,
)


def main(no_ruff: bool) -> None:
    _update_dev_requirements(no_ruff)


def _update_dev_requirements(no_ruff: bool) -> None:
    if not has_pyproject_package_name():
        return
    with ModifiablePyproject.load() as pyproject:
        supported_python_versions = pyproject.get_supported_python_versions()
        if "3.6" in supported_python_versions:
            return
        packages = {
            "jupyterlab-git",
            "jupyterlab-lsp",
            "jupyterlab-myst",
            "jupyterlab",
            "python-lsp-server[rope]",
        }
        if not no_ruff:
            pyproject.remove_dependency("black", ignored_sections=["doc", "test"])
            pyproject.remove_dependency("isort")
            pyproject.remove_dependency("jupyterlab-code-formatter")
            ruff_packages = {
                "jupyterlab-code-formatter >=3.0.0",
                "python-lsp-ruff",
            }
            packages.update(ruff_packages)
        for package in sorted(packages):
            pyproject.add_dependency(package, optional_key=["jupyter", "dev"])
