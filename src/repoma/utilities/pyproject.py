"""Tools for loading and inspecting :code:`pyproject.toml`."""
from collections import OrderedDict
from typing import Optional

import toml

from repoma.utilities import CONFIG_PATH


def load_pyproject(content: Optional[str] = None) -> dict:
    if content is None:
        with open(CONFIG_PATH.pyproject) as stream:
            return toml.load(stream, _dict=OrderedDict)
    return toml.loads(content, _dict=OrderedDict)
