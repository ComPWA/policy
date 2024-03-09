"""Update the developer setup when using Jupyter notebooks."""

from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import PyprojectTOML, get_build_system


def main() -> None:
    _update_dev_requirements()


def _update_dev_requirements() -> None:
    if get_build_system() is None:
        return
    pyproject = PyprojectTOML.load()
    supported_python_versions = pyproject.get_supported_python_versions()
    if "3.6" in supported_python_versions:
        return
    executor = Executor()
    for package in [
        "black",
        "isort",
        "jupyterlab",
        "jupyterlab-code-formatter",
        "jupyterlab-git",
        "jupyterlab-lsp",
        "jupyterlab-myst",
        "python-lsp-ruff",
        "python-lsp-server[rope]",
    ]:
        executor(pyproject.add_dependency, package, optional_key=["jupyter", "dev"])
    executor.finalize()
