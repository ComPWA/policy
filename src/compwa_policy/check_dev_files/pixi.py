"""Update pixi implementation."""

from tomlkit import inline_table

from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.toml import to_toml_array


def main() -> None:
    with ModifiablePyproject.load() as pyproject:
        _configure_setuptools_scm(pyproject)
        _update_dev_environment(pyproject)


def _configure_setuptools_scm(pyproject: ModifiablePyproject) -> None:
    """Configure :code:`setuptools_scm` to not include git info in package version."""
    if not pyproject.has_table("tool.setuptools_scm"):
        return
    setuptools_scm = pyproject.get_table("tool.setuptools_scm")
    expected_scheme = "no-local-version"
    if setuptools_scm.get("local_scheme") != expected_scheme:
        setuptools_scm["local_scheme"] = expected_scheme
        msg = "Configured setuptools_scm to not include git info in package version for pixi"
        pyproject.append_to_changelog(msg)


def _update_dev_environment(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("project.optional-dependencies"):
        return
    optional_dependencies = sorted(pyproject.get_table("project.optional-dependencies"))
    expected = inline_table()
    expected.update({
        "features": to_toml_array(optional_dependencies),
        "solve-group": "default",
    })
    environments = pyproject.get_table("tool.pixi.environments", create=True)
    package_name = pyproject.get_package_name(raise_on_missing=True)
    if environments.get(package_name) != expected:
        environments[package_name] = expected
        msg = "Updated Pixi developer environment"
        pyproject.append_to_changelog(msg)
