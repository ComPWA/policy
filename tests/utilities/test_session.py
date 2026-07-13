from __future__ import annotations

import json
from typing import TYPE_CHECKING, ClassVar

from compwa_policy.repo.gitpod import _extract_extensions
from compwa_policy.utilities import (
    append_safe,
    remove_configs,
    remove_lines,
    rename_file,
    vscode,
)
from compwa_policy.utilities.pyproject import Pyproject
from compwa_policy.utilities.readme import add_badge
from compwa_policy.utilities.resource import Changelog, ModifiableResource
from compwa_policy.utilities.session import Session

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class CountingResource(ModifiableResource):
    loads: ClassVar[int] = 0
    dumps: ClassVar[int] = 0

    def __init__(self) -> None:
        self._changelog: Changelog = []

    @classmethod
    def load(cls) -> CountingResource:
        cls.loads += 1
        return cls()

    @property
    def changelog(self) -> Changelog:
        return self._changelog

    def dump(self) -> None:
        type(self).dumps += 1


def describe_session() -> None:
    def loads_resources_once_and_dumps_them_once_on_flush() -> None:
        CountingResource.loads = 0
        CountingResource.dumps = 0
        with Session() as session:
            first = session.get(CountingResource)
            second = session.get(CountingResource)
            first.changelog.append("Changed counting resource")
            assert first is second
            assert session.flush() == ["Changed counting resource"]
            assert session.flush() == ["Changed counting resource"]
        assert CountingResource.loads == 1
        assert CountingResource.dumps == 1

    def defers_file_helper_changes_until_flush(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_path = vscode_dir / "settings.json"
        settings_path.write_text('{"remove": true}\n')
        extensions_path = vscode_dir / "extensions.json"
        extensions_path.write_text('{"recommendations": []}\n')
        readme_path = tmp_path / "README.md"
        readme_path.write_text("# Title\n")
        obsolete_path = tmp_path / ".obsolete.yml"
        obsolete_path.touch()

        with Session() as session:
            vscode.remove_settings(session, ["remove"])
            vscode.update_settings(session, {"added": True})
            vscode.add_extension_recommendation(session, "Example.Extension")
            add_badge(session, "[![Badge](badge.svg)](example.org)")
            remove_configs(session, [str(obsolete_path)])

            assert json.loads(settings_path.read_text()) == {"remove": True}
            assert json.loads(extensions_path.read_text()) == {"recommendations": []}
            assert readme_path.read_text() == "# Title\n"
            assert obsolete_path.exists()
            assert session.collect_changes()

        assert json.loads(settings_path.read_text()) == {"added": True}
        assert json.loads(extensions_path.read_text()) == {
            "recommendations": ["example.extension"]
        }
        assert "[![Badge](badge.svg)](example.org)" in readme_path.read_text()
        assert not obsolete_path.exists()

    def distinguishes_resources_by_path(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            first = session.get_path(tmp_path / "first.txt")
            same = session.get_path(tmp_path / "first.txt")
            other = session.get_path(tmp_path / "other.txt")
            assert first is same
            assert first is not other

    def shares_deferred_state_between_file_operations(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        source = tmp_path / "source.txt"
        source.write_text("keep\nremove\n")
        renamed = tmp_path / "renamed.txt"

        with Session() as session:
            remove_lines(session, source, "remove")
            assert append_safe(session, "added", source)
            rename_file(session, str(source), str(renamed))
            assert source.read_text() == "keep\nremove\n"
            assert not renamed.exists()

        assert not source.exists()
        assert renamed.read_text() == "keep\nadded\n"


def describe_pyproject_load() -> None:
    def uses_session_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "example"\n')
        with Session() as session:
            assert Pyproject.load(session=session) is session.pyproject


def describe_extract_extensions() -> None:
    def reads_in_memory_vscode_extensions(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "extensions.json").write_text('{"recommendations": []}\n')
        with Session() as session:
            vscode.add_extension_recommendation(session, "Example.Extension")
            assert _extract_extensions(session) == ["example.extension"]
