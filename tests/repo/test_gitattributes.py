from pathlib import Path

import pytest

from compwa_policy.repo.gitattributes import EXPECTED_LINE, check
from compwa_policy.utilities.session import Session


def describe_check():
    def creates_missing_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_check
    ):
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            run_check(check, session)
        assert (tmp_path / ".gitattributes").read_bytes() == b"* text=auto eol=lf\n"

    def prepends_to_existing_attributes(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_check
    ):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / ".gitattributes"
        path.write_bytes(b"*.png binary\n")
        with Session() as session:
            run_check(check, session)
            changes = session.collect_changes()
        assert any(EXPECTED_LINE in m for m in changes)
        assert path.read_bytes() == b"* text=auto eol=lf\n*.png binary\n"

    def leaves_compliant_file_unchanged(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_check
    ):
        monkeypatch.chdir(tmp_path)
        content = b"pixi.lock linguist-generated=true\n* text=auto eol=lf\n"
        path = tmp_path / ".gitattributes"
        path.write_bytes(content)
        with Session() as session:
            run_check(check, session)
            assert not session.collect_changes()
        assert path.read_bytes() == content
