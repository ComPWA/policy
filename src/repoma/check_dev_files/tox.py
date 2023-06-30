"""Check contents of a ``tox.ini`` file."""

from repoma.utilities import CONFIG_PATH
from repoma.utilities.cfg import extract_config_section
from repoma.utilities.executor import Executor


def main() -> None:
    if not CONFIG_PATH.tox.exists():
        return
    executor = Executor()
    executor(
        extract_config_section,
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.pytest,
        sections=["coverage:run", "pytest"],
    )
    executor.finalize()
