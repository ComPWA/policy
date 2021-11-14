import io
from pathlib import Path
from textwrap import dedent

import pytest

from repoma._utilities import (
    copy_config,
    format_config,
    get_precommit_repos,
    get_repo_url,
    open_config,
    open_setup_cfg,
)
from repoma.errors import PrecommitError


def test_copy_config():
    cfg = open_setup_cfg()
    cfg_copy = copy_config(cfg)
    assert cfg_copy is not cfg
    assert cfg_copy == cfg


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
            name = repo-maintenance    # comment
            """,
            """\
            [metadata]
            name = repo-maintenance  # comment
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
            name = repo-maintenance


            """,
            """\
            [metadata]
            name = repo-maintenance
            """,
        ),
        (  # only two whitelines
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
    assert get_repo_url() == "https://github.com/ComPWA/repo-maintenance"


def test_get_precommit_repos():
    repos = get_precommit_repos()
    repo_names = {repo_def["repo"] for repo_def in repos}
    assert repo_names >= {
        "https://github.com/pre-commit/pre-commit-hooks",
        "https://github.com/psf/black",
        "https://github.com/pycqa/pydocstyle",
    }


def test_open_config_exception():
    path = "non-existent.cfg"
    with pytest.raises(
        PrecommitError, match=fr'^Config file "{path}" does not exist$'
    ):
        open_config(path)


def test_open_config_from_path():
    cfg_from_str = open_config(".flake8")
    assert cfg_from_str.sections() == ["flake8"]
    cfg_from_path = open_config(Path(".flake8"))
    assert cfg_from_path == cfg_from_str


def test_open_config_from_stream():
    content = dedent(
        """\
        [section1]
        option1 =
            some_setting = false
        option2 = two

        [section2]
        option3 =
            =src
        """
    )
    print(content)
    stream = io.StringIO(content)
    cfg = open_config(stream)
    assert cfg.sections() == ["section1", "section2"]
    assert cfg.get("section1", "option2") == "two"


def test_open_setup_cfg():
    cfg = open_setup_cfg()
    sections = cfg.sections()
    assert sections == [
        "metadata",
        "options",
        "options.extras_require",
        "options.entry_points",
        "options.packages.find",
        "options.package_data",
    ]
    assert cfg.get("metadata", "name") == "repo-maintenance"
