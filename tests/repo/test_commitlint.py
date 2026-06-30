from pathlib import Path

import pytest

from compwa_policy.repo.commitlint import main


def describe_main():
    def is_noop_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        assert not main()  # nothing to remove

    def removes_outdated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "commitlint.config.js"
        config.touch()
        changes = main()
        assert any("Remove outdated commitlint.config.js" in m for m in changes)
        assert not config.exists()
