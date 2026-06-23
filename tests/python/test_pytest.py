import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.pytest import _deny_ini_options, _update_codecov_settings
from compwa_policy.utilities.pyproject import ModifiablePyproject


def test_deny_ini_options_ignores_missing_pytest_table():
    with ModifiablePyproject.load("""
        [project]
        name = "my-package"
    """) as pyproject:
        _deny_ini_options(pyproject)
        assert pyproject.changelog == []


def test_update_codecov_settings_can_disable_branch_coverage():
    with (
        pytest.raises(PrecommitError, match=r"Updated pytest coverage settings"),
        ModifiablePyproject.load("""
            [project]
            name = "x"

            [dependency-groups]
            test = ["pytest-cov"]
        """) as pyproject,
    ):
        _update_codecov_settings(pyproject, branch_coverage=False)
    coverage = pyproject.get_table("tool.coverage.run")
    assert coverage["branch"] is False
