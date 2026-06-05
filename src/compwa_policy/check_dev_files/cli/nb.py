"""``policy nb`` — Jupyter, nbstripout, Binder."""

from __future__ import annotations

from compwa_policy.check_dev_files.cli import _checks
from compwa_policy.check_dev_files.cli._options import (
    AllowedCellMetadata,
    DevPythonVersion,
    DocAptPackages,
    NoBinder,
    NoRuff,
    PackageManager,
    build_arguments,
)


def nb(  # noqa: PLR0917
    package_manager: PackageManager = "uv",
    dev_python_version: DevPythonVersion = "3.13",
    no_binder: NoBinder = False,
    no_ruff: NoRuff = False,
    allowed_cell_metadata: AllowedCellMetadata = "",
    doc_apt_packages: DocAptPackages = "",
) -> None:
    """Standardize Jupyter notebook config: Jupyter, nbstripout, Binder."""
    args = build_arguments(
        package_manager=package_manager,
        dev_python_version=dev_python_version,
        no_binder=no_binder,
        no_ruff=no_ruff,
        allowed_cell_metadata=allowed_cell_metadata,
        doc_apt_packages=doc_apt_packages,
    )
    _checks.dispatch(args, "nb")
