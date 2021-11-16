# pylint: disable=no-self-use, redefined-outer-name
import io
from pathlib import Path
from textwrap import dedent

import pytest

from repoma._utilities import (
    PrecommitConfig,
    copy_config,
    format_config,
    get_repo_url,
    open_config,
    open_setup_cfg,
)
from repoma.errors import PrecommitError


@pytest.fixture(scope="session")
def dummy_config() -> PrecommitConfig:
    this_dir = Path(__file__).parent
    return PrecommitConfig.load(this_dir / "dummy-pre-commit-config.yml")


class TestPrecommitConfig:
    @pytest.fixture(scope="session")
    def dummy_config(self) -> PrecommitConfig:
        this_dir = Path(__file__).parent
        return PrecommitConfig.load(this_dir / "dummy-pre-commit-config.yml")

    def test_find_repo(self, dummy_config: PrecommitConfig):
        repo = dummy_config.find_repo("non-existent")
        assert repo is None
        repo = dummy_config.find_repo("meta")
        assert repo is not None
        assert repo.repo == "meta"
        assert len(repo.hooks) == 2
        repo = dummy_config.find_repo("black")
        assert repo is not None
        assert repo.repo == "https://github.com/psf/black"

    def test_get_repo_index(self, dummy_config: PrecommitConfig):
        assert dummy_config.get_repo_index("non-existent") is None
        assert dummy_config.get_repo_index("meta") == 0
        assert dummy_config.get_repo_index("pre-commit-hooks") == 1
        assert dummy_config.get_repo_index(r"^.*/pre-commit-hooks$") == 1
        assert dummy_config.get_repo_index("https://github.com/psf/black") == 2

    def test_load(self, dummy_config: PrecommitConfig):
        assert dummy_config.ci is not None
        assert dummy_config.ci.autoupdate_schedule == "monthly"
        assert dummy_config.ci.skip == ["flake8", "mypy"]
        assert len(dummy_config.repos) == 4

    def test_load_default(self):
        config = PrecommitConfig.load()
        repo_names = {repo.repo for repo in config.repos}
        assert repo_names >= {
            "https://github.com/pre-commit/pre-commit-hooks",
            "https://github.com/psf/black",
            "https://github.com/pycqa/pydocstyle",
        }


class TestRepo:
    def test_get_hook_index(self, dummy_config: PrecommitConfig):
        repo = dummy_config.find_repo("local")
        assert repo is not None
        assert repo.get_hook_index("non-existent") is None
        assert repo.get_hook_index("flake8") == 0
        assert repo.get_hook_index("mypy") == 1


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
