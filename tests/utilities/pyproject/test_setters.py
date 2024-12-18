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
    src = """
        [project]
        name = "my-package"
    """
    pyproject = load_pyproject_toml(src, modifiable=True)
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
    src = """
        [project]
        dependencies = ["attrs"]
        [project.optional-dependencies]
        lint = ["ruff"]
    """
    pyproject = load_pyproject_toml(src, modifiable=True)
    updated = add_dependency(pyproject, "attrs")
    assert updated is False

    updated = add_dependency(pyproject, "ruff", optional_key="lint")
    assert updated is False


def test_add_dependency_nested():
    src = dedent("""
        [project]
        name = "my-package"
    """)
    pyproject = load_pyproject_toml(src, modifiable=True)
    add_dependency(pyproject, "ruff", optional_key=["lint", "style", "dev"])
    new_content = tomlkit.dumps(pyproject)
    expected = dedent("""
        [project]
        name = "my-package"

        [project.optional-dependencies]
        lint = ["ruff"]
        style = ["my-package[lint]"]
        dev = ["my-package[style]"]
    """)
    assert new_content == expected

    pyproject = load_pyproject_toml(src, modifiable=True)
    add_dependency(pyproject, "ruff", optional_key=["lint"])
    new_content = tomlkit.dumps(pyproject)
    expected = dedent("""
        [project]
        name = "my-package"

        [project.optional-dependencies]
        lint = ["ruff"]
    """)
    assert new_content == expected


def test_add_dependency_optional():
    src = dedent("""
        [project]
        name = "my-package"
    """)
    pyproject = load_pyproject_toml(src, modifiable=True)
    add_dependency(pyproject, "ruff", optional_key="lint")

    new_content = tomlkit.dumps(pyproject)
    expected = dedent("""
        [project]
        name = "my-package"

        [project.optional-dependencies]
        lint = ["ruff"]
    """)
    assert new_content == expected


@pytest.fixture
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
        style = ["ruff"]
    """)
    return load_pyproject_toml(src, modifiable=True)


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
        style = ["ruff"]
    """)
    new_content = tomlkit.dumps(pyproject_example)
    assert new_content == expected


def test_remove_dependency_nested(pyproject_example: PyprojectTOML):
    remove_dependency(pyproject_example, "ruff", ignored_sections=["sty", "style"])
    new_content = tomlkit.dumps(pyproject_example)
    expected = dedent("""
        [project]
        name = "my-package"
        dependencies = ["attrs"]

        [project.optional-dependencies]
        lint = [
            "mypy",
        ]
        style = ["ruff"]
    """)
    assert new_content == expected


@pytest.mark.parametrize("table_key", ["project", "project.optional-dependencies"])
def test_create_sub_table(table_key: str):
    pyproject = load_pyproject_toml("", modifiable=True)
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


def test_create_sub_table_with_super_table():
    pyproject = load_pyproject_toml("", modifiable=True)
    pixi = create_sub_table(pyproject, "tool.pixi")
    pixi["channels"] = ["conda-forge"]
    pixi["platforms"] = ["linux-64"]
    task_table = create_sub_table(pyproject, "tool.pixi.feature.dev.tasks.test")
    task_table["cmd"] = "pytest"

    new_content = tomlkit.dumps(pyproject)
    expected = dedent("""
        [tool.pixi]
        channels = ["conda-forge"]
        platforms = ["linux-64"]

        [tool.pixi.feature.dev.tasks.test]
        cmd = "pytest"
    """)
    assert new_content.strip() == expected.strip()
