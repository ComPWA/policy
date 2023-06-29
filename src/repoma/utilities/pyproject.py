"""Tools for loading and inspecting :code:`pyproject.toml`."""
from typing import Optional

import tomlkit
from tomlkit.toml_document import TOMLDocument

from repoma.utilities import CONFIG_PATH


def load_pyproject(content: Optional[str] = None) -> TOMLDocument:
    if content is None:
        with open(CONFIG_PATH.pyproject) as stream:
            return tomlkit.loads(stream.read())
    return tomlkit.loads(content)
