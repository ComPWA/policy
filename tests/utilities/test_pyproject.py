from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject
from compwa_policy.utilities.toml import to_toml_array

POLICY_REPO_DIR = Path(__file__).absolute().parent.parent.parent


def describe_load():
    @pytest.mark.parametrize("path", [None, POLICY_REPO_DIR / "pyproject.toml"])
    def reads_from_path(path: Path | None):
        if path is None:
            pyproject = Pyproject.load()
        else:
            pyproject = Pyproject.load(path)
        assert "build-system" in pyproject._document
        assert "tool" in pyproject._document

    def reads_from_str():
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
        assert set(pyproject._document) == {
            "build-system",
            "project",
        }
        project = pyproject.get_table("project")
        assert project.get("dependencies") == [
            "attrs",
            "sympy >=1.10",
        ]

    def raises_type_error_for_unsupported_source():
        with pytest.raises(TypeError, match="Source of type int is not supported"):
            _ = Pyproject.load(1)  # ty:ignore[invalid-argument-type]

    def get_table_accepts_none_as_fallback():
        pyproject = Pyproject.load("""
            [project]
            name = "my-package"
        """)
        assert pyproject.get_table("tool.pytest", fallback=None) is None


def describe_edit_and_dump():
    def preserves_table_order(tmp_path: Path):
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            dedent("""
                [project]
                name = "my-package"

                [dependency-groups]
                dev = ["pytest"]
            """)
        )
        pyproject = ModifiablePyproject.load(pyproject_path)

        pyproject.dump()

        result = pyproject_path.read_text()
        assert result.index("[project]") < result.index("[dependency-groups]")

    def creates_and_modifies_tables():
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
            tools["black"] = to_toml_array(["--line-length=79"], multiline=True)

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


def describe_move_dependencies_to_group():
    def leaves_missing_packages_unchanged(tmp_path: Path):
        path = tmp_path / "pyproject.toml"
        path.write_text(
            dedent("""\
            [project]
            name = "x"
            """)
        )
        with ModifiablePyproject.load(path) as pyproject:
            pyproject.move_dependencies_to_group(["ruff", "ty"], "dev")
            assert not pyproject.changelog
            assert "dependency-groups" not in pyproject.dumps()

    def moves_packages_from_different_sections(tmp_path: Path):
        path = tmp_path / "pyproject.toml"
        path.write_text(
            dedent("""\
            [project]
            name = "x"
            dependencies = ["ruff>=0.1", "attrs"]

            [project.optional-dependencies]
            style = ["ty>=0.2"]

            [dependency-groups]
            dev = [{ include-group = "style" }]
            style = []
            """)
        )
        with ModifiablePyproject.load(path) as pyproject:
            pyproject.move_dependencies_to_group(("ruff", "ty"), "dev")
        with ModifiablePyproject.load(path) as pyproject:
            assert list(pyproject.get_table("project")["dependencies"]) == ["attrs"]
            assert (
                list(pyproject.get_table("project.optional-dependencies")["style"])
                == []
            )
            assert list(pyproject.get_table("dependency-groups")["dev"]) == [
                {"include-group": "style"},
                "ruff>=0.1",
                "ty>=0.2",
            ]
            pyproject.move_dependencies_to_group(["ruff", "ty"], "dev")
            assert not pyproject.changelog


def describe_move_single_dependency_to_group():
    @pytest.mark.parametrize("tool", ["ruff", "ty"])
    def moves_tools_to_dev_preserving_constraints(tmp_path: Path, tool: str):
        path = tmp_path / "pyproject.toml"
        path.write_text(
            dedent(f"""\
            [project]
            name = "x"

            [dependency-groups]
            dev = [{{ include-group = "style" }}]
            style = ["{tool}>=0.1"]
            types = ["{tool}>=0.1", "types-PyYAML"]
            """)
        )
        with ModifiablePyproject.load(path) as pyproject:
            pyproject.move_dependencies_to_group([tool], "dev")
        with ModifiablePyproject.load(path) as pyproject:
            groups = pyproject.get_table("dependency-groups")
            assert list(groups["dev"]) == [{"include-group": "style"}, f"{tool}>=0.1"]
            assert list(groups["style"]) == []
            assert list(groups["types"]) == ["types-PyYAML"]
            pyproject.move_dependencies_to_group([tool], "dev")
            assert not pyproject.changelog
