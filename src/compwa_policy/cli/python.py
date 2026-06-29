"""``policy python`` — checks for pyproject, Ruff, Black, mypy, pyright, ty, pytest, pyupgrade."""

from __future__ import annotations

from compwa_policy.cli import _checks
from compwa_policy.cli._options import (
    AllowVscodeCoverageGutters,
    BranchCoverage,
    DevPythonVersion,
    ExcludedPythonVersions,
    ImportsOnTop,
    NoRuff,
    PytestSingleThreaded,
    Python,
    TypeCheckerOption,
    build_arguments,
)


def python(  # noqa: PLR0917
    python: Python = None,
    dev_python_version: DevPythonVersion = None,
    excluded_python_versions: ExcludedPythonVersions = None,
    type_checker: TypeCheckerOption = None,
    no_ruff: NoRuff = None,
    imports_on_top: ImportsOnTop = None,
    branch_coverage: BranchCoverage = None,
    pytest_single_threaded: PytestSingleThreaded = None,
    allow_vscode_coverage_gutters: AllowVscodeCoverageGutters = None,
) -> None:
    """Standardize Python tooling: pyproject, Ruff, Black, mypy, pyright, ty, pytest, pyupgrade."""
    args = build_arguments(
        python=python,
        dev_python_version=dev_python_version,
        excluded_python_versions=excluded_python_versions,
        type_checker=type_checker,
        no_ruff=no_ruff,
        imports_on_top=imports_on_top,
        branch_coverage=branch_coverage,
        pytest_single_threaded=pytest_single_threaded,
        allow_vscode_coverage_gutters=allow_vscode_coverage_gutters,
    )
    _checks.dispatch(args, "python")
