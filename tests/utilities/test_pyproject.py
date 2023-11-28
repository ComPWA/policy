from pathlib import Path
from textwrap import dedent
from typing import Optional

import pytest
from tomlkit.items import Table

from repoma.utilities.pyproject import load_pyproject

REPOMA_DIR = Path(__file__).absolute().parent.parent.parent


@pytest.mark.parametrize("path", [None, REPOMA_DIR / "pyproject.toml"])
def test_load_pyproject(path: Optional[Path]):
    if path is None:
        pyproject = load_pyproject()
    else:
        pyproject = load_pyproject(path)
    assert "build-system" in pyproject
    assert "tool" in pyproject


def test_load_pyproject_str():
    src = dedent("""
    [build-system]
    build-backend = "setuptools.build_meta"
    requires = [
        "setuptools>=61.2",
        "setuptools_scm",
    ]

    [project]
    dependencies = [
        "attrs",
        "sympy >=1.10",
    ]
    name = "my-package"
    requires-python = ">=3.7"
    """)
    pyproject = load_pyproject(src)
    assert isinstance(pyproject["build-system"], Table)
    assert pyproject["project"]["dependencies"] == ["attrs", "sympy >=1.10"]  # type: ignore[index]


def test_load_pyproject_type_error():
    with pytest.raises(TypeError, match="Source of type int is not supported"):
        _ = load_pyproject(1)  # type: ignore[arg-type]
