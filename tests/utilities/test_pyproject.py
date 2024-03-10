from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from tomlkit.items import Table

from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject
from compwa_policy.utilities.toml import to_toml_array

POLICY_REPO_DIR = Path(__file__).absolute().parent.parent.parent


class TestPyprojectToml:
    @pytest.mark.parametrize("path", [None, POLICY_REPO_DIR / "pyproject.toml"])
    def test_load_from_path(self, path: Path | None):
        if path is None:
            pyproject = Pyproject.load()
        else:
            pyproject = Pyproject.load(path)
        assert "build-system" in pyproject._document
        assert "tool" in pyproject._document

    def test_load_from_str(self):
        pyproject = Pyproject.load("""
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
        assert isinstance(pyproject._document["build-system"], Table)
        assert pyproject._document["project"]["dependencies"] == [  # type: ignore[index]
            "attrs",
            "sympy >=1.10",
        ]

    def test_load_type_error(self):
        with pytest.raises(TypeError, match="Source of type int is not supported"):
            _ = Pyproject.load(1)  # type: ignore[arg-type]


def test_edit_and_dump():
    src = dedent("""
        [owner]
        name = "John Smith"
        age = 30
        [owner.address]
        city = "Wonderland"
        street = "123 Main St"
    """)
    with ModifiablePyproject.load(src) as pyproject:
        address = pyproject.get_table("owner.address")
        address["city"] = "New York"
        work = pyproject.get_table("owner.work", create=True)
        work["type"] = "scientist"
        tools = pyproject.get_table("tool", create=True)
        tools["black"] = to_toml_array(["--line-length=79"], enforce_multiline=True)

    new_content = pyproject.dumps()
    expected = dedent("""
        [owner]
        name = "John Smith"
        age = 30
        [owner.address]
        city = "New York"
        street = "123 Main St"

        [owner.work]
        type = "scientist"

        [tool]
        black = [
            "--line-length=79",
        ]
    """)
    assert new_content.strip() == expected.strip()
