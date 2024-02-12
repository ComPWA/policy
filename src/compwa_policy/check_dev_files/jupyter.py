"""Update the developer setup when using Jupyter notebooks."""

from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.project_info import (
    get_supported_python_versions,
    is_package,
)
from compwa_policy.utilities.pyproject import add_dependency


def main() -> None:
    _update_dev_requirements()


def _update_dev_requirements() -> None:
    if not is_package():
        return
    if "3.6" in get_supported_python_versions():
        return
    hierarchy = ["jupyter", "dev"]
    dependencies = [
        "black",
        "isort",
        "jupyterlab",
        "jupyterlab-code-formatter",
        "jupyterlab-git",
        "jupyterlab-lsp",
        "jupyterlab-myst",
        "python-lsp-ruff",
        "python-lsp-server[rope]",
    ]
    executor = Executor()
    for dependency in dependencies:
        executor(add_dependency, dependency, optional_key=hierarchy)
    executor.finalize()
