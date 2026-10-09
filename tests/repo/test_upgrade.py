from __future__ import annotations

import runpy
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from compwa_policy.repo.upgrade import get_uv_upgrade_script

if TYPE_CHECKING:
    from pathlib import Path


def describe_uv_upgrade_script():
    @pytest.mark.parametrize("return_codes", [(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    def upgrades_every_project(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, return_codes: tuple[int, ...]
    ):
        directories = []

        def run(command: list[str], **_kwargs) -> SimpleNamespace:
            if command == ["git", "ls-files"]:
                return SimpleNamespace(
                    returncode=0,
                    stdout="pyproject.toml\ndocs/a/pyproject.toml\ndocs/b/pyproject.toml\nREADME.md\n",
                )
            assert command[:4] == ["uv", "lock", "--upgrade", "--directory"]
            directories.append(command[4])
            return SimpleNamespace(returncode=return_codes[len(directories) - 1])

        monkeypatch.setattr("subprocess.run", run)
        script = tmp_path / "upgrade.py"
        script.write_text(get_uv_upgrade_script())
        with pytest.raises(SystemExit) as exception:
            runpy.run_path(str(script))

        assert directories == [".", "docs/a", "docs/b"]
        assert exception.value.code == (not all(code == 0 for code in return_codes))
