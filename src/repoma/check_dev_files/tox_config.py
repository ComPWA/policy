"""Check contents of a ``tox.ini`` file."""

from repoma._utilities import CONFIG_PATH, extract_config_section


def check_tox_ini() -> None:
    if not CONFIG_PATH.tox.exists():
        return
    extract_config_section(
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.flake8,
        sections=["flake8"],
    )
    extract_config_section(
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.pydocstyle,
        sections=["pydocstyle"],
    )
    extract_config_section(
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.pytest,
        sections=["coverage:run", "pytest"],
    )
