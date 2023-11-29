"""Update the developer setup when using Jupyter notebooks."""

from repoma.utilities.executor import Executor
from repoma.utilities.project_info import get_supported_python_versions
from repoma.utilities.pyproject import add_dependency


def main() -> None:
    _update_dev_requirements()


def _update_dev_requirements() -> None:
    if "3.6" in get_supported_python_versions():
        return
    hierarchy = ["jupyter", "dev"]
    dependencies = [
        "jupyterlab",
        "jupyterlab-code-formatter",
        "jupyterlab-lsp",
        "jupyterlab-myst",
        "python-lsp-server[rope]",
    ]
    executor = Executor()
    for dependency in dependencies:
        executor(add_dependency, dependency, optional_key=hierarchy)
    executor.finalize()
