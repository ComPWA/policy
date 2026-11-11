import contextlib
from pathlib import Path

import pytest

from compwa_policy.errors import PolicyError
from compwa_policy.repo.gitpod import (
    _extract_extensions,
    _generate_gitpod_config,
    check,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session


def describe_generate_gitpod_config():
    def builds_expected_sections():
        with Session() as session:
            gitpod_content = _generate_gitpod_config(session, python_version="3.8")
        assert set(gitpod_content) == {
            "github",
            "tasks",
            "vscode",
        }
        assert gitpod_content["github"] == {
            "prebuilds": {
                "addBadge": False,
                "addComment": False,
                "addLabel": False,
                "branches": False,
                "master": True,
                "pullRequests": True,
                "pullRequestsFromForks": True,
            }
        }
        assert gitpod_content["tasks"] == [
            {"init": "pyenv local 3.8"},
            {"init": "pip install -e .[dev]"},
        ]
        with Session() as session:
            assert gitpod_content["vscode"]["extensions"] == _extract_extensions(
                session
            )


def describe_check():
    @pytest.mark.parametrize(
        ("enable", "expect_config"),
        [(set(), False), ({"gitpod"}, True)],
        ids=["default", "enabled"],
    )
    def manages_config_only_when_enabled(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run_check,
        enable: set[str],
        expect_config: bool,
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitpod.yml").write_text("tasks: []\n")
        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text("repos: []\n")
        precommit = ModifiablePrecommit.load(config)
        with contextlib.suppress(PolicyError), Session.load(precommit) as session:
            run_check(check, session, enable=enable)
        assert (tmp_path / ".gitpod.yml").exists() is expect_config
