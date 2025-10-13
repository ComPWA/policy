from typing import Literal

PythonVersion = Literal[
    "3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"
]
PYTHON_VERSIONS = set(PythonVersion.__args__)  # type:ignore[attr-defined]
DEFAULT_DEV_PYTHON_VERSION: PythonVersion = "3.13"
