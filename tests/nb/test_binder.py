import os
import stat
from pathlib import Path

import pytest

from compwa_policy.nb import binder
from compwa_policy.utilities.session import Session

# cspell:ignore nenv


def describe_main():
    def configures_uv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            binder.main(session, "uv", "3.12", ["graphviz"])
            changes = session.collect_changes()
        assert changes
        assert (tmp_path / ".binder" / "apt.txt").read_text() == "graphviz\n"
        assert (tmp_path / ".binder" / "runtime.txt").read_text() == "python-3.12\n"
        post_build = (tmp_path / ".binder" / "postBuild").read_text()
        assert "astral.sh/uv/install.sh" in post_build

    def configures_pixi_with_activation(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pixi.toml").write_text(
            '[activation]\nscripts = ["setup.sh"]\nenv = {MY_VAR = "1"}\n'
        )
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\n\n[dependency-groups]\njupyter = ["jupyterlab"]\n'
        )
        with Session() as session:
            binder.main(session, "pixi+uv", "3.12", [])
            changes = session.collect_changes()
        assert changes
        post_build = (tmp_path / ".binder" / "postBuild").read_text()
        assert "pixi.sh/install.sh" in post_build
        assert 'export MY_VAR="1"' in post_build
        assert "bash setup.sh" in post_build
        assert "--group jupyter" in post_build


def describe_update_apt_txt():
    def removes_when_no_packages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        apt_txt = tmp_path / ".binder" / "apt.txt"
        apt_txt.parent.mkdir()
        apt_txt.write_text("graphviz\n")
        changes = binder._update_apt_txt([])
        assert any("Removed" in m for m in changes)
        assert not apt_txt.exists()

    def is_noop_when_no_packages_and_absent(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        binder._update_apt_txt([])  # no packages, no file -> no changes


def describe_update_post_build():
    def raises_for_unsupported_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with (
            pytest.raises(NotImplementedError, match=r"conda is not supported"),
            Session() as session,
        ):
            binder._update_post_build(session, package_manager="conda")


def describe_make_executable():
    def sets_executable_bit(tmp_path: Path):
        script = tmp_path / "postBuild"
        script.write_text("#!/bin/bash\n")
        script.chmod(0o644)
        changes = binder._make_executable(script)
        assert any("made executable" in m for m in changes)
        assert os.access(script, os.X_OK)

    def is_noop_when_already_executable(tmp_path: Path):
        script = tmp_path / "postBuild"
        script.write_text("#!/bin/bash\n")
        script.chmod(0o755)
        binder._make_executable(script)  # already executable -> no changes
        assert script.stat().st_mode & stat.S_IXUSR
