from compwa_policy.python.pytest import _deny_ini_options
from compwa_policy.utilities.pyproject import ModifiablePyproject


def test_deny_ini_options_ignores_missing_pytest_table():
    with ModifiablePyproject.load("""
        [project]
        name = "my-package"
    """) as pyproject:
        _deny_ini_options(pyproject)
        assert pyproject.changelog == []
