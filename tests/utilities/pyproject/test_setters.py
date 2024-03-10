from textwrap import dedent

import pytest
import tomlkit

from compwa_policy.utilities.pyproject import load_pyproject_toml
from compwa_policy.utilities.pyproject._struct import PyprojectTOML
from compwa_policy.utilities.pyproject.setters import (
    add_dependency,
    create_sub_table,
    remove_dependency,
)


def test_add_dependency():
    pyproject = load_pyproject_toml("""
        [project]
        name = "my-package"
    """)
    updated = add_dependency(pyproject, "attrs")
    assert updated is True

    new_content = tomlkit.dumps(pyproject)
    expected = """
        [project]
        name = "my-package"
        dependencies = ["attrs"]
    """
    assert new_content == expected


def test_add_dependency_existing():
    pyproject = load_pyproject_toml("""
        [project]
        dependencies = ["attrs"]

        [project.optional-dependencies]
        lint = ["ruff"]
    """)
    updated = add_dependency(pyproject, "attrs")
    assert updated is False

    updated = add_dependency(pyproject, "ruff", optional_key="lint")
    assert updated is False


def test_add_dependency_nested():
    src = dedent("""
        [project]
        name = "my-package"
    """)

    pyproject = load_pyproject_toml(src)
    add_dependency(pyproject, "ruff", optional_key=["lint", "sty", "dev"])

    new_content = tomlkit.dumps(pyproject)
    expected = dedent("""
        [project]
        name = "my-package"

        [project.optional-dependencies]
        lint = ["ruff"]
        sty = ["my-package[lint]"]
        dev = ["my-package[sty]"]
    """)
    assert new_content == expected


def test_add_dependency_optional():
    src = dedent("""
        [project]
        name = "my-package"
    """)
    pyproject = load_pyproject_toml(src)
    add_dependency(pyproject, "ruff", optional_key="lint")

    new_content = tomlkit.dumps(pyproject)
    expected = dedent("""
        [project]
        name = "my-package"

        [project.optional-dependencies]
        lint = ["ruff"]
    """)
    assert new_content == expected


@pytest.fixture(scope="function")
def pyproject_example() -> PyprojectTOML:
    src = dedent("""
        [project]
        name = "my-package"
        dependencies = ["attrs", "ruff"]

        [project.optional-dependencies]
        lint = [
            "mypy",
            "ruff",
        ]
        sty = ["ruff"]
    """)
    return load_pyproject_toml(src)


def test_remove_dependency(pyproject_example: PyprojectTOML):
    remove_dependency(pyproject_example, "attrs")
    expected = dedent("""
        [project]
        name = "my-package"
        dependencies = ["ruff"]

        [project.optional-dependencies]
        lint = [
            "mypy",
            "ruff",
        ]
        sty = ["ruff"]
    """)
    new_content = tomlkit.dumps(pyproject_example)
    assert new_content == expected


def test_remove_dependency_nested(pyproject_example: PyprojectTOML):
    remove_dependency(pyproject_example, "ruff", ignored_sections=["sty"])
    new_content = tomlkit.dumps(pyproject_example)
    expected = dedent("""
        [project]
        name = "my-package"
        dependencies = ["attrs"]

        [project.optional-dependencies]
        lint = [
            "mypy",
        ]
        sty = ["ruff"]
    """)
    assert new_content == expected


@pytest.mark.parametrize("table_key", ["project", "project.optional-dependencies"])
def test_create_sub_table(table_key: str):
    pyproject = load_pyproject_toml("")
    dependencies = create_sub_table(pyproject, table_key)

    new_content = tomlkit.dumps(pyproject)
    expected = dedent(f"""
        [{table_key}]
    """)
    assert new_content.strip() == expected.strip()

    dependencies["lint"] = ["ruff"]
    new_content = tomlkit.dumps(pyproject)
    expected = dedent(f"""
        [{table_key}]
        lint = ["ruff"]
    """)
    assert new_content.strip() == expected.strip()
