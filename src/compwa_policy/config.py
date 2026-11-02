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
