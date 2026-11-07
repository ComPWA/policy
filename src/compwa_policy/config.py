import sys
from typing import Literal

if sys.version_info >= (3, 12):
    from typing import TypeAliasType
else:
    from typing_extensions import TypeAliasType

PythonVersion = Literal[
    "3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "3.15"
]
PYTHON_VERSIONS = set(PythonVersion.__args__)
DEFAULT_DEV_PYTHON_VERSION: PythonVersion = "3.14"

PackageManagerChoice = Literal["none", "uv", "conda", "pixi+uv", "pixi", "venv"]
"""Package managers supported by the policy framework."""

TypeChecker = Literal["mypy", "pyright", "ty"]
"""Type checkers supported by the policy framework."""

DependabotEcosystem = Literal["github-actions", "julia", "pre-commit", "uv"]
"""Package ecosystems that the Dependabot configuration can update."""

UpgradeFrequency = Literal["monthly", "quarterly", "semiannually"]
"""Frequencies supported for updating lock files."""

MacosRunnerLabel = TypeAliasType(
    "MacosRunnerLabel",
    Literal[
        "macos-14",
        "macos-14-large",
        "macos-14-xlarge",
        "macos-15",
        "macos-15-intel",
        "macos-15-large",
        "macos-15-xlarge",
        "macos-26",
        "macos-26-intel",
        "macos-26-large",
        "macos-26-xlarge",
        "macos-latest",
        "macos-latest-large",
    ],
)
"""Supported runner labels from GitHub's public image table."""

UbuntuRunnerLabel = TypeAliasType(
    "UbuntuRunnerLabel",
    Literal[
        "ubuntu-22.04",
        "ubuntu-22.04-arm",
        "ubuntu-24.04",
        "ubuntu-24.04-arm",
        "ubuntu-26.04",
        "ubuntu-26.04-arm",
        "ubuntu-latest",
        "ubuntu-slim",
    ],
)
"""Supported runner labels from GitHub's public image table."""
