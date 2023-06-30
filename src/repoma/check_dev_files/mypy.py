"""Check and update :code:`mypy` settings."""
import os

import tomlkit
from ini2toml.api import Translator

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.pyproject import get_sub_table, load_pyproject, write_pyproject


def main() -> None:
    _merge_mypy_into_pyproject()


def _merge_mypy_into_pyproject() -> None:
    config_path = ".mypy.ini"
    if not os.path.exists(config_path):
        return
    with open(config_path) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name=config_path)
    mypy_config = tomlkit.parse(toml_str)
    pyproject = load_pyproject()
    tool_table = get_sub_table(pyproject, "tool", create=True)
    tool_table.update(mypy_config)
    write_pyproject(pyproject)
    os.remove(config_path)
    msg = f"Moved mypy configuration to {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)
