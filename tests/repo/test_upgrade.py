from __future__ import annotations

import runpy
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest

from compwa_policy.repo.upgrade import get_uv_upgrade_script


def describe_get_uv_upgrade_script():
    @pytest.mark.parametrize(
        "return_codes", [(0, 0, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)]
    )
    def upgrades_every_project_and_script(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, return_codes: tuple[int, ...]
    ):
        targets = []

        def run(command: list[str], **_kwargs) -> SimpleNamespace:
            if command == ["git", "ls-files"]:
                return SimpleNamespace(
                    returncode=0,
                    stdout=dedent("""\
                        pyproject.toml
                        docs/a/pyproject.toml
                        docs/b/pyproject.toml
                        README.md
                        scripts/bench.py
                        scripts/bench.py.lock
                        """),
                )
            assert command[:3] == ["uv", "lock", "--upgrade"]
            targets.append(command[3:])
            return SimpleNamespace(returncode=return_codes[len(targets) - 1])

        monkeypatch.setattr("subprocess.run", run)
        script = tmp_path / "upgrade.py"
        script.write_text(get_uv_upgrade_script(), encoding="utf-8", newline="\n")
        with pytest.raises(SystemExit) as exception:
            runpy.run_path(str(script))

        assert targets == [
            ["--directory", "."],
            ["--directory", str(Path("docs/a"))],
            ["--directory", str(Path("docs/b"))],
            ["--script", str(Path("scripts/bench.py"))],
        ]
        assert exception.value.code == (not all(code == 0 for code in return_codes))
