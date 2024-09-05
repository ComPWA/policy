"""Check and update :code:`pytest` settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import rtoml
from ini2toml.api import Translator

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.cfg import open_config
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from tomlkit.items import Array


def main() -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_merge_coverage_into_pyproject, pyproject)
        do(_merge_pytest_into_pyproject, pyproject)
        do(_update_settings, pyproject)


def _merge_coverage_into_pyproject(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.pytest_ini.exists():
        return
    pytest_ini = open_config(CONFIG_PATH.pytest_ini)
    section_name = "coverage:run"
    if not pytest_ini.has_section(section_name):
        return
    coverage_config: dict = dict(pytest_ini[section_name])
    for key, value in coverage_config.items():
        if value in {"False", "True"}:
            coverage_config[key] = bool(value)
        if key == "source" and isinstance(value, str):
            coverage_config[key] = [value]
    tool_table = pyproject.get_table("tool.coverage.run", create=True)
    tool_table.update(coverage_config)
    msg = f"Imported Coverage.py configuration from {CONFIG_PATH.pytest_ini}"
    pyproject.changelog.append(msg)


def _merge_pytest_into_pyproject(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.pytest_ini.exists():
        return
    with open(CONFIG_PATH.pytest_ini) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name="pytest.ini")
    pytest_config = rtoml.loads(toml_str)
    pytest_config.pop("coverage:run", None)
    tool_table = pyproject.get_table("tool", create=True)
    tool_table.update(pytest_config)
    CONFIG_PATH.pytest_ini.unlink()
    msg = f"Imported pytest configuration from {CONFIG_PATH.pytest_ini}"
    pyproject.changelog.append(msg)


def _update_settings(pyproject: ModifiablePyproject) -> None:
    table_key = "tool.pytest.ini_options"
    if not pyproject.has_table(table_key):
        return
    config = pyproject.get_table(table_key)
    existing = config.get("addopts", "")
    expected = __get_expected_addopts(existing)
    if isinstance(existing, str) or sorted(existing) != sorted(expected):
        config["addopts"] = expected
        msg = f"Updated [{table_key}]"
        pyproject.changelog.append(msg)


def __get_expected_addopts(existing: str | Iterable) -> Array:
    if isinstance(existing, str):
        options = {opt.strip() for opt in __split_options(existing)}
    else:
        options = set(existing)
    options = {opt for opt in options if opt and not opt.startswith("--color=")}
    options.add("--color=yes")
    return to_toml_array(sorted(options))


def __split_options(arg: str) -> list[str]:
    """Split a string of options into a list of options.

    >>> __split_options('-abc def -ghi "j k l" -mno pqr')
    ['-abc def', '-ghi "j k l"', '-mno pqr']
    """
    elements = arg.split()
    options: list[str] = []
    for i in range(len(elements)):
        if i > 0 and not elements[i].startswith("-"):
            options[-1] += f" {elements[i]}"
        else:
            options.append(elements[i])
    return options
