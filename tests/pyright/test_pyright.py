import io
import re
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.pyright import (
    _merge_config_into_pyproject,
    _update_precommit,
    _update_settings,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


def test_merge_config_into_pyproject(this_dir: Path):
    input_stream = io.StringIO()
    old_config_path = this_dir / "pyrightconfig.json"
    with (
        pytest.raises(
            PrecommitError,
            match=re.escape(f"Imported pyright configuration from {old_config_path}"),
        ),
        ModifiablePyproject.load(input_stream) as pyproject,
    ):
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


def test_update_precommit():
    bad_config = dedent("""
        repos:
          - repo: meta
            hooks:
              - id: check-hooks-apply
    """).lstrip()
    with (
        pytest.raises(PrecommitError),
        ModifiablePrecommit.load(io.StringIO(bad_config)) as precommit,
    ):
        _update_precommit(precommit)

    expected = dedent("""
        repos:
          - repo: meta
            hooks:
              - id: check-hooks-apply

          - repo: https://github.com/ComPWA/pyright-pre-commit
            rev: PLEASE-UPDATE
            hooks:
              - id: pyright
    """).lstrip()
    assert precommit.dumps() == expected


def test_update_settings():
    bad_config = dedent("""
        [tool.pyright]
        include = ["**/*.py"]
        reportUnusedImport = true
    """).lstrip()
    with (
        pytest.raises(PrecommitError, match=r"Updated pyright configuration"),
        ModifiablePyproject.load(io.StringIO(bad_config)) as pyproject,
    ):
        _update_settings(pyproject)

    result = pyproject.dumps()
    expected_result = dedent("""
        [tool.pyright]
        include = ["**/*.py"]
        reportUnusedImport = true
        typeCheckingMode = "strict"
        venv = ".venv"
        venvPath = "."
    """)
    assert result.strip() == expected_result.strip()
