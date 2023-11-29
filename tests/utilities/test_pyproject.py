import io
from pathlib import Path
from textwrap import dedent, indent
from typing import Optional

import pytest
from tomlkit.items import Table

from repoma.errors import PrecommitError
from repoma.utilities.pyproject import (
    add_dependency,
    get_package_name_safe,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)

REPOMA_DIR = Path(__file__).absolute().parent.parent.parent


def test_add_dependency():
    stream = io.StringIO(dedent("""
    [project]
    name = "my-package"
    """))
    stream.seek(0)
    dependency = "attrs"
    with pytest.raises(
        PrecommitError,
        match=f"Listed {dependency} as a dependency under pyproject.toml",
    ):
        add_dependency(dependency, source=stream)
    result = stream.getvalue()
    print(result)  # noqa: T201  # run with pytest -s
    assert result == dedent("""
    [project]
    name = "my-package"
    dependencies = ["attrs"]
    """)


def test_add_dependency_nested():
    stream = io.StringIO(dedent("""
    [project]
    name = "my-package"
    """))
    stream.seek(0)
    with pytest.raises(PrecommitError):
        add_dependency("ruff", optional_key=["lint", "sty", "dev"], source=stream)
    result = stream.getvalue()
    print(result)  # noqa: T201  # run with pytest -s
    assert result == dedent("""
    [project]
    name = "my-package"

    [project.optional-dependencies]
    lint = ["ruff"]
    sty = ["my-package[lint]"]
    dev = ["my-package[sty]"]
    """)


def test_add_dependency_optional():
    stream = io.StringIO(dedent("""
    [project]
    name = "my-package"
    """))
    stream.seek(0)
    with pytest.raises(PrecommitError):
        add_dependency("ruff", optional_key="lint", source=stream)
    result = stream.getvalue()
    print(result)  # noqa: T201  # run with pytest -s
    assert result == dedent("""
    [project]
    name = "my-package"

    [project.optional-dependencies]
    lint = ["ruff"]
    """)


def test_edit_toml():
    src = dedent("""
    [owner]
    name = "John Smith"
    age = 30

    [owner.address]
    city = "Wonderland"
    street = "123 Main St"
    """)
    config = load_pyproject(src)

    address = get_sub_table(config, "owner.address")
    address["city"] = "New York"
    work = get_sub_table(config, "owner.work", create=True)
    work["type"] = "scientist"
    tools = get_sub_table(config, "tool", create=True)
    tools["black"] = to_toml_array(["--line-length=79"], enforce_multiline=True)

    stream = io.StringIO()
    write_pyproject(config, target=stream)
    result = stream.getvalue()
    print(indent(result, prefix=4 * " "))  # noqa: T201  # run with pytest -s
    assert result == dedent("""
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


def test_get_package_name_safe():
    correct_input = io.StringIO(dedent("""
    [project]
    name = "my-package"
    """))
    assert get_package_name_safe(correct_input) == "my-package"

    with pytest.raises(PrecommitError, match=r"^Please provide a name for the package"):
        _ = get_package_name_safe(io.StringIO("[project]"))
    with pytest.raises(PrecommitError, match=r"^Please provide a name for the package"):
        _ = get_package_name_safe(io.StringIO())


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
