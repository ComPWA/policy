"""Update `setuptools_scm <https://setuptools-scm.rtfd.io>`_ configuration."""

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import ModifiablePyproject, complies_with_subset


def main() -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    with ModifiablePyproject.load() as pyproject:
        if not pyproject.has_table("tool.setuptools_scm"):
            return
        setuptools_scm = pyproject.get_table("tool.setuptools_scm")
        expected_scheme = {
            "local_scheme": "no-local-version",
            "version_scheme": "only-version",
        }
        if not complies_with_subset(setuptools_scm, expected_scheme):
            setuptools_scm.update(expected_scheme)
            msg = "Configured setuptools_scm to not include git info in package version"
            pyproject.changelog.append(msg)
