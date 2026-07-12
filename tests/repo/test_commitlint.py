from pathlib import Path

import pytest

from compwa_policy.repo.commitlint import main
from compwa_policy.utilities.session import Session


def describe_main():
    def is_noop_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            main(session)  # nothing to remove
            assert not session.collect_changes()

    def removes_outdated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "commitlint.config.js"
        config.touch()
        with Session() as session:
            main(session)
            changes = session.collect_changes()
        assert any("Remove outdated commitlint.config.js" in m for m in changes)
        assert not config.exists()
