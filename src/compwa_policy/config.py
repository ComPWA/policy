from typing import Literal

PythonVersion = Literal[
    "3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "3.15"
]
PYTHON_VERSIONS = set(PythonVersion.__args__)
DEFAULT_DEV_PYTHON_VERSION: PythonVersion = "3.14"

PackageManagerChoice = Literal["none", "uv", "conda", "pixi+uv", "pixi", "venv"]
"""Package managers supported by the policy framework."""

Tool = Literal[
    "binder",
    "cspell",
    "docstrfmt",
    "editorconfig",
    "github-actions",
    "gitpod",
    "labels",
    "nbstripout",
    "prettier",
    "pyupgrade",
    "ruff",
]
"""Tools that a repository can switch on or off through ``enable`` and ``disable``.

A check declares the tool it manages by passing its name to
`~compwa_policy.utilities.check_hook.check_hook`.
"""
OPT_IN_TOOLS: frozenset[Tool] = frozenset({"gitpod"})
"""Tools that policy only manages when they are listed under ``enable``."""

TypeChecker = Literal["mypy", "pyright", "ty"]
"""Type checkers supported by the policy framework."""

DependabotEcosystem = Literal["github-actions", "julia", "pre-commit", "uv"]
"""Package ecosystems that the Dependabot configuration can update."""

UpgradeFrequency = Literal["monthly", "quarterly", "semiannually"]
"""Frequencies supported for updating lock files."""

MacosRunnerLabel = Literal[
    "macos-14",
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
]
"""Supported runner labels from GitHub's public image table."""

UbuntuRunnerLabel = Literal[
    "ubuntu-22.04",
    "ubuntu-22.04-arm",
    "ubuntu-24.04",
    "ubuntu-24.04-arm",
    "ubuntu-26.04",
    "ubuntu-26.04-arm",
    "ubuntu-latest",
    "ubuntu-slim",
]
"""Supported runner labels from GitHub's public image table."""
