# cspell:ignore fstring
import io
from configparser import ConfigParser
from textwrap import dedent
from typing import Optional, Type

import pytest

from repoma.check_dev_files.flake8 import (
    _check_comments_on_separate_line,
    _check_missing_options,
    _check_option_order,
    _check_setup_cfg,
    _move_comments_before_line,
)
from repoma.errors import PrecommitError


def test_check_comments_on_separate_line():
    stream = io.StringIO(
        """
        ignore = # some comment
        """
    )
    with pytest.raises(
        PrecommitError,
        match=r"^Please move the comment on the following line.*",
    ):
        _check_comments_on_separate_line(stream)


def test_check_setup_cfg_correct():
    content = """
        [options.extras_require]
        flake8 =
            flake8 >=4  # extend-select
            flake8-blind-except
            flake8-bugbear
            flake8-builtins
            flake8-comprehensions
            flake8-pytest-style
            flake8-rst-docstrings
            flake8-type-ignore; python_version >="3.8.0"
            flake8-use-fstring
            package-that-is-ignored
            pep8-naming
        """
    content = dedent(content)
    cfg = ConfigParser()
    cfg.read_string(content)
    _check_setup_cfg(cfg)


@pytest.mark.parametrize(
    "content",
    [
        """
        [options.extras_require]
        lint =
            flake8 >=4  # extend-select
            flake8-blind-except
            flake8-bugbear
            flake8-builtins
            flake8-comprehensions
            flake8-pytest-style
            flake8-rst-docstrings
            flake8-type-ignore
            flake8-use-fstring
            pep8-naming
        """,
        """
        [options.extras_require]
        lint =
            flake8
            flake8-bugbear
        """,
    ],
)
def test_check_setup_cfg_incorrect(content: str):
    content = dedent(content)
    cfg = ConfigParser()
    cfg.read_string(content)
    with pytest.raises(PrecommitError) as error:
        _check_setup_cfg(cfg)
    assert (
        error.value.args[0]
        == dedent(
            """
        Section [options.extras_require] in setup.cfg should look like this:

        [options.extras_require]
        ...
        flake8 =
            flake8 >=4  # extend-select
            flake8-blind-except
            flake8-bugbear
            flake8-builtins
            flake8-comprehensions
            flake8-pytest-style
            flake8-rst-docstrings
            flake8-type-ignore; python_version >="3.8.0"
            flake8-use-fstring
            pep8-naming
        ...
        lint =
            %(flake8)s
            ...
        sty =
            ...
            %(lint)s
            ...
        dev =
            ...
            %(sty)s
            ...
        """
        ).strip()
    )


@pytest.mark.parametrize(
    ("unformatted", "expected"),
    [
        (
            """
            ignore =
                E231  # allowed by black
            """,
            """
            ignore =
                # allowed by black
                E231
            """,
        ),
    ],
)
def test_move_comments_before_line(unformatted: str, expected: str):
    unformatted = dedent(unformatted)
    expected = dedent(expected)
    formatted = _move_comments_before_line(unformatted)
    assert formatted == expected


@pytest.mark.parametrize(
    "content",
    [
        """\
        [section]
        option =
            v8
            v9
            v10
        """,
        """\
        [section]
        option =
            value_a
            value_b
        """,
        """\
        [section]
        option =
            a
            B
        """,
    ],
)
def test_check_option_order_correct(content: str):
    content = dedent(content)
    cfg = ConfigParser()
    cfg.read_string(content)
    _check_option_order(cfg)


@pytest.mark.parametrize(
    "content",
    [
        """\
        [section]
        option =
            b
            a
        """,
    ],
)
def test_check_option_order_incorrect(content: str):
    content = dedent(content)
    cfg = ConfigParser()
    cfg.read_string(content)
    with pytest.raises(
        PrecommitError,
        match=r'Option "option" in section \[section\] is not sorted',
    ):
        _check_option_order(cfg)


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (
            """\
            [flake8]
            extend-select =
                TC
                TI100
            """,
            None,
        ),
        (
            """\
            [flake8]
            extend-select =
                b
                a
            """,
            ValueError,
        ),
        ("", ValueError),
    ],
)
def test_check_extend_select(content: str, error: Optional[Type[ValueError]]):
    content = dedent(content)
    cfg = ConfigParser()
    cfg.read_string(content)
    execute_command = lambda: _check_missing_options(  # noqa: E731
        cfg=cfg,
        option="extend-select",
        expected_values=["TC"],
    )
    if error is None:
        execute_command()
    else:
        with pytest.raises(
            PrecommitError, match=r"^Flake8 config is missing an option"
        ):
            execute_command()
