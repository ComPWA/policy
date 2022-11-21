# pylint: disable=redefined-outer-name
from pathlib import Path

import pytest

from repoma.utilities.precommit import (
    Hook,
    PrecommitCi,
    PrecommitConfig,
    Repo,
    fromdict,
)


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


def test_fromdict():
    hook_def = {"id": "test"}
    hook = Hook(id="test")
    assert fromdict(hook_def, Hook) == hook

    repo_def = {"repo": "url", "hooks": [hook_def]}
    repo = Repo(repo="url", hooks=[hook])
    assert fromdict(repo_def, Repo) == repo

    ci_def = {"autofix_prs": False}
    ci = PrecommitCi(autofix_prs=False)  # pylint: disable=invalid-name
    assert fromdict(ci_def, PrecommitCi) == ci

    config_def = {"repos": [repo_def], "ci": ci_def}
    config = PrecommitConfig(repos=[repo], ci=ci)
    assert fromdict(config_def, PrecommitConfig) == config
