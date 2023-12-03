"""Check and update :code:`pytest` settings."""

from __future__ import annotations

import os

import tomlkit
from ini2toml.api import Translator

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.cfg import open_config
from repoma.utilities.executor import Executor
from repoma.utilities.pyproject import get_sub_table, load_pyproject, write_pyproject

__PYTEST_INI_PATH = "pytest.ini"


def main() -> None:
    executor = Executor()
    executor(_merge_coverage_into_pyproject)
    executor(_merge_pytest_into_pyproject)
    executor(_remove_pytest_ini)
    executor.finalize()


def _merge_coverage_into_pyproject() -> None:
    if not os.path.exists(__PYTEST_INI_PATH):
        return
    pytest_ini = open_config(__PYTEST_INI_PATH)
    section_name = "coverage:run"
    if not pytest_ini.has_section(section_name):
        return
    coverage_config: dict = dict(pytest_ini[section_name])
    for key, value in coverage_config.items():
        if value in {"False", "True"}:
            coverage_config[key] = bool(value)
        if key == "source" and isinstance(value, str):
            coverage_config[key] = [value]
    pyproject = load_pyproject()
    tool_table = get_sub_table(pyproject, "tool.coverage.run", create=True)
    tool_table.update(coverage_config)
    write_pyproject(pyproject)
    msg = f"Moved Coverage.py configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _merge_pytest_into_pyproject() -> None:
    if not os.path.exists(__PYTEST_INI_PATH):
        return
    with open(__PYTEST_INI_PATH) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name=__PYTEST_INI_PATH)
    config = tomlkit.parse(toml_str)
    config.pop("coverage:run", None)
    pyproject = load_pyproject()
    tool_table = get_sub_table(pyproject, "tool", create=True)
    tool_table.update(config)
    write_pyproject(pyproject)
    msg = f"Moved pytest configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _remove_pytest_ini() -> None:
    if not os.path.exists(__PYTEST_INI_PATH):
        return
    os.remove(__PYTEST_INI_PATH)
    msg = f"Removed {__PYTEST_INI_PATH}"
    raise PrecommitError(msg)
