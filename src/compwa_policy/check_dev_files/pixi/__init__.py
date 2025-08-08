"""Update pixi implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from compwa_policy.check_dev_files.pixi._helpers import has_pixi_config
from compwa_policy.check_dev_files.pixi._remove import remove_pixi_configuration
from compwa_policy.check_dev_files.pixi._update import update_pixi_configuration

if TYPE_CHECKING:
    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.utilities.pyproject.getters import PythonVersion

__all__ = [
    "has_pixi_config",
    "main",
]


def main(
    package_manager: PackageManagerChoice,
    is_python_package: bool,
    dev_python_version: PythonVersion,
) -> None:
    if "pixi" in package_manager:
        update_pixi_configuration(
            is_python_package,
            dev_python_version,
            package_manager,
        )
    else:
        remove_pixi_configuration()
