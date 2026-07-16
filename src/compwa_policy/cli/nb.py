"""``policy nb`` — Jupyter, nbstripout, Binder."""

from __future__ import annotations

from compwa_policy.cli import _checks
from compwa_policy.cli._options import (
    AllowedCellMetadata,
    DevPythonVersion,
    DocAptPackages,
    ExcludeDependency,
    NoBinder,
    NoRuff,
    PackageManager,
    build_arguments,
)


def nb(  # noqa: PLR0917
    package_manager: PackageManager = None,
    dev_python_version: DevPythonVersion = None,
    no_binder: NoBinder = None,
    no_ruff: NoRuff = None,
    allowed_cell_metadata: AllowedCellMetadata = None,
    doc_apt_packages: DocAptPackages = None,
    exclude_dependency: ExcludeDependency = None,
) -> None:
    """Standardize Jupyter notebook config: Jupyter, nbstripout, Binder."""
    args = build_arguments(
        package_manager=package_manager,
        dev_python_version=dev_python_version,
        no_binder=no_binder,
        no_ruff=no_ruff,
        allowed_cell_metadata=allowed_cell_metadata,
        doc_apt_packages=doc_apt_packages,
        excluded_dependencies=exclude_dependency,
    )
    _checks.dispatch(args, "nb")
