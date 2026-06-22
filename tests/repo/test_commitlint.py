from pathlib import Path

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.repo.commitlint import main


def describe_main():
    def is_noop_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        main()  # no error and nothing to remove

    def removes_outdated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "commitlint.config.js"
        config.touch()
        with pytest.raises(
            PrecommitError, match=r"Remove outdated commitlint\.config\.js"
        ):
            main()
        assert not config.exists()
