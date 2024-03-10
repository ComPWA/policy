import io
from pathlib import Path

import pytest

from compwa_policy.utilities.precommit.getters import (
    find_repo,
    find_repo_with_index,
    load_precommit_config,
)


@pytest.fixture(scope="session")
def example_yaml() -> str:
    config_path = Path(__file__).parent / ".pre-commit-config.yaml"
    with open(config_path) as stream:
        return stream.read()


@pytest.mark.parametrize("use_stream", [True, False])
def test_load_precommit_config(example_yaml: str, use_stream: bool):
    if use_stream:
        stream = io.StringIO(example_yaml)
        config = load_precommit_config(stream)
    else:
        config = load_precommit_config(example_yaml)
    assert set(config) == {"ci", "repos"}

    ci = config.get("ci")
    assert ci is not None
    assert ci.get("autoupdate_schedule") == "quarterly"

    repos = config.get("repos")
    assert repos is not None
    assert len(repos) == 3


def test_load_precommit_config_path():
    config = load_precommit_config()
    assert "ci" in config
    ci = config.get("ci")
    assert ci is not None
    assert ci.get("autoupdate_commit_msg") == "MAINT: autoupdate pre-commit hooks"


def test_find_repo(example_yaml: str):
    config = load_precommit_config(example_yaml)
    repo = find_repo(config, "ComPWA/policy")
    assert repo is not None
    assert repo["repo"] == "https://github.com/ComPWA/policy"
    assert repo["rev"] == "0.3.0"
    assert len(repo["hooks"]) == 1


def test_find_repo_with_index(example_yaml: str):
    config = load_precommit_config(example_yaml)

    repo_and_idx = find_repo_with_index(config, "ComPWA/policy")
    assert repo_and_idx is not None
    index, repo = repo_and_idx
    assert index == 1
    assert repo["repo"] == "https://github.com/ComPWA/policy"

    assert find_repo_with_index(config, "non-existent") is None
