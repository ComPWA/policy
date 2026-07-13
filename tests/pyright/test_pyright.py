import json
import re
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.python.pyright import (
    _merge_config_into_pyproject,
    _remove_excludes,
    _remove_pyright,
    _update_precommit,
    _update_settings,
    _update_vscode_settings,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.session import Session


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


def _write_pyproject(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(dedent(content).lstrip())
    return path


def _write_precommit(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".pre-commit-config.yaml"
    path.write_text(dedent(content).lstrip())
    return path


def describe_merge_config_into_pyproject():
    def is_noop_without_config(tmp_path: Path):
        pyproject_path = _write_pyproject(tmp_path, "[project]\nname = 'x'\n")
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _merge_config_into_pyproject(pyproject, tmp_path / "pyrightconfig.json")

    def imports_from_json(this_dir: Path, tmp_path: Path):
        pyproject_path = _write_pyproject(tmp_path, "")
        old_config_path = this_dir / "pyrightconfig.json"
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _merge_config_into_pyproject(pyproject, old_config_path, remove=False)
        assert any(
            re.search(
                rf"Imported pyright configuration from {re.escape(str(old_config_path))}",
                m,
            )
            for m in pyproject.changelog
        )
        expected_result = dedent("""
            [tool.pyright]
            include = ["src/**/*.py"]
            exclude = ["tests/**/*.py"]
            pythonVersion = "3.9"
            reportMissingTypeStubs = false
            reportMissingImports = true
        """)
        assert pyproject_path.read_text().strip() == expected_result.strip()


def describe_update_precommit():
    def adds_pyright_hook(tmp_path: Path):
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
            """,
        )
        with ModifiablePrecommit.load(config) as precommit:
            _update_precommit(precommit)
        assert precommit.changelog  # something changed
        expected = dedent("""
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply

              - repo: https://github.com/ComPWA/pyright-pre-commit
                rev: PLEASE-UPDATE
                hooks:
                  - id: pyright
        """).lstrip()
        assert precommit.dumps() == expected


def describe_update_settings():
    def adds_strict_settings(tmp_path: Path):
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [tool.pyright]
            include = ["**/*.py"]
            reportUnusedImport = true
            """,
        )
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _update_settings(pyproject)
        assert any("Updated pyright configuration" in m for m in pyproject.changelog)
        expected_result = dedent("""
            [tool.pyright]
            include = ["**/*.py"]
            reportUnusedImport = true
            typeCheckingMode = "strict"
            venv = ".venv"
            venvPath = "."
        """)
        assert pyproject.dumps().strip() == expected_result.strip()


def describe_remove_excludes():
    def removes_exclude_key(tmp_path: Path):
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [tool.pyright]
            include = ["src"]
            exclude = ["tests"]
            """,
        )
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _remove_excludes(pyproject)
        assert any("Removed pyright excludes" in m for m in pyproject.changelog)
        assert "exclude" not in pyproject.get_table("tool.pyright")

    def is_noop_without_exclude(tmp_path: Path):
        pyproject_path = _write_pyproject(
            tmp_path, '[tool.pyright]\ninclude = ["src"]\n'
        )
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _remove_excludes(pyproject)

    def is_noop_without_pyright_table(tmp_path: Path):
        pyproject_path = _write_pyproject(tmp_path, "[project]\nname = 'x'\n")
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _remove_excludes(pyproject)


def describe_update_vscode_settings():
    def recommends_pylance_when_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            _update_vscode_settings(active=True, session=session)
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "ms-python.vscode-pylance" in extensions["recommendations"]

    def removes_pylance_when_inactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "extensions.json").write_text(
            json.dumps({"recommendations": ["ms-python.vscode-pylance"]})
        )
        with Session() as session:
            _update_vscode_settings(active=False, session=session)
        extensions = json.loads((vscode_dir / "extensions.json").read_text())
        assert "ms-python.vscode-pylance" not in extensions.get("recommendations", [])


def describe_remove_pyright():
    def removes_config_and_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyrightconfig.json").write_text("{}")
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [project]
            name = "x"

            [tool.pyright]
            typeCheckingMode = "strict"

            [dependency-groups]
            style = ["pyright"]
            """,
        )
        precommit_path = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: https://github.com/ComPWA/pyright-pre-commit
                rev: v1.1.0
                hooks:
                  - id: pyright
            """,
        )
        with (
            ModifiablePrecommit.load(precommit_path) as precommit,
            ModifiablePyproject.load(pyproject_path) as pyproject,
            Session(precommit=precommit, pyproject=pyproject) as session,
        ):
            _remove_pyright(session=session)
        assert not (tmp_path / "pyrightconfig.json").exists()
        assert "tool.pyright" not in pyproject.dumps()
        assert "id: pyright" not in precommit.dumps()


def describe_main():
    def configures_everything_when_active(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path, '[project]\nname = "x"\n')
        precommit_path = _write_precommit(tmp_path, "repos: []\n")
        precommit = ModifiablePrecommit.load(precommit_path)
        with Session.load(precommit) as session:
            main(session, active=True)
        pyproject_text = (tmp_path / "pyproject.toml").read_text()
        assert "typeCheckingMode" in pyproject_text
        assert "id: pyright" in precommit.dumps()
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "ms-python.vscode-pylance" in extensions["recommendations"]

    def removes_pyright_when_inactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(
            tmp_path,
            '[project]\nname = "x"\n\n[tool.pyright]\ntypeCheckingMode = "strict"\n',
        )
        precommit_path = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: https://github.com/ComPWA/pyright-pre-commit
                rev: v1.1.0
                hooks:
                  - id: pyright
            """,
        )
        precommit = ModifiablePrecommit.load(precommit_path)
        with Session.load(precommit) as session:
            main(session, active=False)
        assert "tool.pyright" not in (tmp_path / "pyproject.toml").read_text()
        assert "id: pyright" not in precommit.dumps()
