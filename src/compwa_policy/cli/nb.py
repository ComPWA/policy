"""``policy nb`` — Jupyter, nbstripout, Binder."""

from __future__ import annotations

from compwa_policy.cli import _checks
from compwa_policy.cli._options import (
    AllowedCellMetadata,
    DevPythonVersion,
    Disable,
    DocAptPackages,
    ExcludeDependency,
    PackageManager,
    build_arguments,
)


def nb(  # ruff: ignore[too-many-positional-arguments]
    package_manager: PackageManager = None,
    dev_python_version: DevPythonVersion = None,
    disable: Disable = None,
    allowed_cell_metadata: AllowedCellMetadata = None,
    doc_apt_packages: DocAptPackages = None,
    exclude_dependency: ExcludeDependency = None,
) -> None:
    """Standardize Jupyter notebook config: Jupyter, nbstripout, Binder."""
    args = build_arguments(
        package_manager=package_manager,
        dev_python_version=dev_python_version,
        disable=disable,
        allowed_cell_metadata=allowed_cell_metadata,
        doc_apt_packages=doc_apt_packages,
        excluded_dependencies=exclude_dependency,
    )
    _checks.dispatch(args, "nb")
