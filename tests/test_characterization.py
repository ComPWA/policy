from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.characterization import (
    characterize_repository,
    detect_package_manager,
    detect_type_checkers,
)


def describe_characterize_repository():
    def detects_python_pixi_uv_and_ty(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        git_init(tmp_path)
        (tmp_path / "module.py").write_text("value = 1\n")
        (tmp_path / "pixi.lock").touch()
        (tmp_path / "uv.lock").touch()
        (tmp_path / "pyproject.toml").write_text("[tool.ty]\n")

        result = characterize_repository()

        assert result.has_python_code is True
        assert result.package_manager == "pixi+uv"
        assert result.type_checkers == {"ty"}


def describe_detect_package_manager():
    def recognizes_conda(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yml").write_text("name: demo\n")

        assert detect_package_manager({}) == "conda"


def describe_detect_type_checkers():
    def combines_configuration_files_and_hooks(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".mypy.ini").write_text("[mypy]\n")
        (tmp_path / ".pre-commit-config.yaml").write_text(
            dedent("""
            repos:
              - repo: local
                hooks:
                  - id: pyright
            """).lstrip()
        )

        assert detect_type_checkers({}) == {"mypy", "pyright"}
