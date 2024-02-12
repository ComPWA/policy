import io
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.cfg import format_config, open_config
from compwa_policy.utilities.project_info import get_repo_url


@pytest.mark.parametrize(
    ("unformatted", "expected"),
    [
        (  # replace tabs
            """\
            folders =
            \tdocs,
            \tsrc,
            """,
            """\
            folders =
                docs,
                src,
            """,
        ),
        (  # remove spaces before comments
            """\
            [metadata]
            name = compwa-policy    # comment
            """,
            """\
            [metadata]
            name = compwa-policy  # comment
            """,
        ),
        (  # remove trailing white-space
            """\
            ends with a tab\t
            ends with some spaces    \n
            """,
            """\
            ends with a tab
            ends with some spaces
            """,
        ),
        (  # end file with one and only one newline
            """\
            [metadata]
            name = compwa-policy


            """,
            """\
            [metadata]
            name = compwa-policy
            """,
        ),
        (  # only two linebreaks
            """\
            [section1]
            option1 = one


            [section2]
            option2 = two
            """,
            """\
            [section1]
            option1 = one

            [section2]
            option2 = two
            """,
        ),
    ],
)
def test_format_config(unformatted: str, expected: str):
    unformatted = dedent(unformatted)
    formatted = io.StringIO()
    format_config(input=io.StringIO(unformatted), output=formatted)
    formatted.seek(0)
    assert formatted.read() == dedent(expected)


def test_get_repo_url():
    assert get_repo_url() == "https://github.com/ComPWA/policy"


def test_open_config_exception():
    path = "non-existent.cfg"
    with pytest.raises(PrecommitError, match=rf'^Config file "{path}" does not exist$'):
        open_config(path)


def test_open_config_from_stream():
    msg = """\
    [section1]
    option1 =
        some_setting = false
    option2 = two

    [section2]
    option3 =
        =src
    """
    content = dedent(msg)
    print(content)
    stream = io.StringIO(content)
    cfg = open_config(stream)
    assert cfg.sections() == ["section1", "section2"]
    assert cfg.get("section1", "option2") == "two"
