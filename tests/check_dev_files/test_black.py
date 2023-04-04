from textwrap import dedent

import pytest

from repoma.check_dev_files.black import (
    _check_activate_preview,
    _check_line_length,
    _check_option_ordering,
    _check_target_versions,
    _load_black_config,
    _load_nbqa_black_config,
)
from repoma.errors import PrecommitError


def test_check_line_length():
    toml_content = dedent("""
        [tool.black]
        line-length = 79
        """).strip()
    config = _load_black_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_line_length(config)
    assert (
        error.value.args[0]
        == "pyproject.toml should not specify a line-length (default to 88)."
    )


@pytest.mark.parametrize(
    "toml_content",
    [
        """[tool.black]""",
        dedent("""
        [tool.config]
        preview = false
        """).strip(),
    ],
)
def test_check_activate_preview(toml_content: str):
    toml_content = """[tool.black]"""
    config = _load_black_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_activate_preview(config)
    assert error.value.args[0] == dedent("""
            An option in pyproject.toml is wrong or missing. Should be:

            [tool.black]
            preview = true
            """).strip()


def test_check_target_versions():
    toml_content = dedent("""
        [tool.black]
        target-version = [
            'py36',
            'py37',
            'py310',
        ]
        """).strip()
    config = _load_black_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_target_versions(config)
    assert error.value.args[0] == dedent("""
            Black target versions in pyproject.toml should be as follows:

            [tool.black]
            target-version = [
                'py310',
                'py311',
                'py36',
                'py37',
                'py38',
                'py39',
            ]
            """).strip()


def test_load_config_from_pyproject():
    config = _load_black_config()
    assert config["preview"] is True
    assert "exclude" in config


def test_load_config_from_string():
    toml_content = dedent(R"""
        [tool.black]
        preview = true
        include = '\.pyi?$'
        line-length = 88
        """).strip()
    config = _load_black_config(toml_content)
    assert config == {
        "preview": True,
        "include": R"\.pyi?$",
        "line-length": 88,
    }


def test_load_nbqa_black_config():
    # cspell:ignore addopts
    toml_content = dedent(R"""
        [tool.nbqa.addopts]
        black = [
            "--line-length=85",
        ]
        """).strip()
    config = _load_nbqa_black_config(toml_content)
    assert config == ["--line-length=85"]


def test_check_option_ordering():
    toml_content = dedent(R"""
        [tool.black]
        preview = true
        line-length = 88
        """).strip()
    config = _load_black_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_option_ordering(config)
    assert error.value.args[0] == dedent("""
            Options in pyproject.toml should be alphabetically sorted:

            [tool.black]
            line-length = ...
            preview = ...
            """).strip()
