import io
import re
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.check_dev_files.pyright import (
    _merge_config_into_pyproject,
    _update_precommit,
    _update_settings,
)
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


def test_merge_config_into_pyproject(this_dir: Path):
    input_stream = io.StringIO()
    old_config_path = this_dir / "pyrightconfig.json"
    with pytest.raises(
        PrecommitError,
        match=re.escape(f"Imported pyright configuration from {old_config_path}"),
    ), ModifiablePyproject.load(input_stream) as pyproject:
        _merge_config_into_pyproject(pyproject, old_config_path, remove=False)

    result = input_stream.getvalue()
    expected_result = dedent("""
        [tool.pyright]
        include = ["src/**/*.py"]
        exclude = ["tests/**/*.py"]
        pythonVersion = "3.9"
        reportMissingTypeStubs = false
        reportMissingImports = true
    """)
    assert result.strip() == expected_result.strip()


def test_update_precommit(this_dir: Path):
    pyproject = Pyproject.load(this_dir / "pyproject-bad.toml")
    with open(this_dir / ".pre-commit-config-bad.yaml") as stream:
        input_stream = io.StringIO(stream.read())
    with pytest.raises(PrecommitError), ModifiablePrecommit.load(
        input_stream
    ) as precommit:
        _update_precommit(precommit, pyproject)

    result = input_stream.getvalue()
    with open(this_dir / ".pre-commit-config-good.yaml") as stream:
        expected_result = stream.read()
    assert result.strip() == expected_result.strip()


def test_update_settings(this_dir: Path):
    with open(this_dir / "pyproject-bad.toml") as stream:
        input_stream = io.StringIO(stream.read())
    with pytest.raises(
        PrecommitError, match=r"Updated pyright configuration"
    ), ModifiablePyproject.load(input_stream) as pyproject:
        _update_settings(pyproject)

    result = input_stream.getvalue()
    expected_result = dedent("""
        [tool.pyright]
        include = ["**/*.py"]
        reportUnusedImport = true
        typeCheckingMode = "strict"
    """)
    assert result.strip() == expected_result.strip()
