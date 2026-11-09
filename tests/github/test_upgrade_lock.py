import io
from collections.abc import Callable
from pathlib import Path

import pytest

from compwa_policy.github.upgrade_lock import check
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml


@pytest.fixture
def lock_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_init: Callable[[Path], None],
    git_add: Callable[[Path], None],
) -> Path:
    git_init(tmp_path)
    (tmp_path / "uv.lock").touch()
    git_add(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run(run_check, *, autofix_ci: bool) -> list[str]:
    precommit = ModifiablePrecommit.load(io.StringIO("repos: []\n"))
    with Session.load(precommit) as session:
        run_check(check, session, autofix_ci=autofix_ci)
        return session.collect_changes()


def describe_check():
    @pytest.mark.parametrize("autofix_ci", [False, True])
    def leaves_pr_upgrades_to_autofix_ci(lock_repo: Path, run_check, autofix_ci: bool):
        assert _run(run_check, autofix_ci=autofix_ci)
        yaml = create_prettier_round_trip_yaml()
        workflow = yaml.load(lock_repo / ".github" / "workflows" / "lock.yml")
        assert ("pull_request" in workflow["on"]) is not autofix_ci
        assert "schedule" in workflow["on"]
        assert workflow["jobs"]["lock"]["secrets"] == {"token": "${{ secrets.PAT }}"}
        assert not _run(run_check, autofix_ci=autofix_ci)
