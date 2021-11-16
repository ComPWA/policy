"""Check contents of a ``tox.ini`` file."""

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, extract_config_section
from repoma.utilities.executor import Executor


def main() -> None:
    if not CONFIG_PATH.tox.exists():
        return
    executor = Executor()
    executor(
        extract_config_section,
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.flake8,
        sections=["flake8"],
    )
    executor(
        extract_config_section,
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.pydocstyle,
        sections=["pydocstyle"],
    )
    executor(
        extract_config_section,
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.pytest,
        sections=["coverage:run", "pytest"],
    )
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())
