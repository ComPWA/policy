from textwrap import dedent

import pytest

from repoma.check_dev_files.black import (
    _check_experimental_string_processing,
    _check_line_length,
    _check_option_ordering,
    _check_target_versions,
    _load_config,
)
from repoma.errors import PrecommitError


def test_check_line_length():
    toml_content = dedent(
        """
        [tool.black]
        line-length = 88
        """
    ).strip()
    config = _load_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_line_length(config)
    assert (
        error.value.args[0]
        == dedent(
            """
            Black line-length in pyproject.toml in pyproject.toml should be:

            [tool.black]
            line-length = 79
            """
        ).strip()
    )


@pytest.mark.parametrize(
    "toml_content",
    [
        """[tool.black]""",
        dedent(
            """
        [tool.config]
        experimental-string-processing = false
        """
        ).strip(),
    ],
)
def test_check_experimental_string_processing(toml_content: str):
    toml_content = """[tool.black]"""
    config = _load_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_experimental_string_processing(config)
    assert (
        error.value.args[0]
        == dedent(
            """
            An option in pyproject.toml is wrong or missing. Should be:

            [tool.black]
            experimental-string-processing = true
            """
        ).strip()
    )


def test_check_target_versions():
    toml_content = dedent(
        """
        [tool.black]
        target-version = [
            'py36',
            'py37',
            'py310',
        ]
        """
    ).strip()
    config = _load_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_target_versions(config)
    assert (
        error.value.args[0]
        == dedent(
            """
            Black target versions in pyproject.toml should be as follows:

            [tool.black]
            target-version = [
                'py36',
                'py37',
                'py38',
                'py39',
            ]
            """
        ).strip()
    )


def test_load_config_from_pyproject():
    config = _load_config()
    assert config["line-length"] == 79
    assert "exclude" in config


def test_load_config_from_string():
    toml_content = dedent(
        R"""
        [tool.black]
        experimental-string-processing = true
        include = '\.pyi?$'
        line-length = 79
        """
    ).strip()
    config = _load_config(toml_content)
    assert config == {
        "experimental-string-processing": True,
        "include": R"\.pyi?$",
        "line-length": 79,
    }


def test_check_option_ordering():
    toml_content = dedent(
        R"""
        [tool.black]
        line-length = 79
        experimental-string-processing = true
        """
    ).strip()
    config = _load_config(toml_content)
    with pytest.raises(PrecommitError) as error:
        _check_option_ordering(config)
    assert (
        error.value.args[0]
        == dedent(
            """
            Options in pyproject.toml should be alphabetically sorted:

            [tool.black]
            experimental-string-processing = ...
            line-length = ...
            """
        ).strip()
    )
