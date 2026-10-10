from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from compwa_policy.github.dependabot import check
from compwa_policy.utilities.session import Session

if TYPE_CHECKING:
    from pathlib import Path


def _read_ecosystems(repo: Path) -> list[str]:
    config = yaml.safe_load((repo / ".github" / "dependabot.yml").read_text())
    return [entry["package-ecosystem"] for entry in config["updates"]]


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, git_commit) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n")
    (tmp_path / "uv.lock").write_text("version = 1\n")
    git_commit(tmp_path)
    return tmp_path


def describe_check() -> None:
    def derives_ecosystems_from_repository_files(repo: Path, run_check) -> None:
        with Session() as session:
            run_check(check, session)
        assert _read_ecosystems(repo) == ["github-actions", "pre-commit", "uv"]

    def lists_only_configured_ecosystems(repo: Path, run_check) -> None:
        with Session() as session:
            run_check(
                check, session, dependabot_ecosystems=["pre-commit", "github-actions"]
            )
        assert _read_ecosystems(repo) == ["github-actions", "pre-commit"]

    def removes_config_for_empty_selection(repo: Path, run_check) -> None:
        with Session() as session:
            run_check(check, session)
        assert (repo / ".github" / "dependabot.yml").exists()
        with Session() as session:
            run_check(check, session, dependabot_ecosystems=[])
            assert session.changelog == ["Removed .github/dependabot.yml"]
        assert not (repo / ".github" / "dependabot.yml").exists()
        with Session() as session:
            run_check(check, session, dependabot_ecosystems=[])
            assert session.changelog == []

    def rejects_unknown_ecosystem(repo: Path, run_check) -> None:
        del repo
        with Session() as session, pytest.raises(ValueError, match="npm"):
            run_check(check, session, dependabot_ecosystems=["npm"])
