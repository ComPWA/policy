import io
from textwrap import dedent

import pytest

from repoma.format_setup_cfg import _format_setup_cfg


@pytest.mark.parametrize(
    ("unformatted", "expected"),
    [
        (
            """\
            [options.extras_require]
            dev =
                tox >= 1.9    # for skip_install, use_develop
            """,
            """\
            [options.extras_require]
            dev =
                tox >=1.9  # for skip_install, use_develop
            """,
        ),
        (
            """\
            numpy>=1.16,<1.21
            pytest==6.2.5
            tox>=1.9
            Sphinx  >= 3
            """,
            """\
            numpy >=1.16, <1.21
            pytest==6.2.5
            tox >=1.9
            Sphinx >=3
            """,
        ),
    ],
)
def test_format_config(unformatted: str, expected: str):
    unformatted = dedent(unformatted)
    formatted = io.StringIO()
    _format_setup_cfg(input=io.StringIO(unformatted), output=formatted)
    formatted.seek(0)
    assert formatted.read() == dedent(expected)
