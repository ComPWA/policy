import io
import json
import re
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
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

# cspell:ignore pylance pyproject pyrightconfig


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


def describe_merge_config_into_pyproject():
    def is_noop_without_config(tmp_path: Path):
        input_stream = io.StringIO("[project]\nname = 'x'\n")
        with ModifiablePyproject.load(input_stream) as pyproject:
            _merge_config_into_pyproject(
                pyproject, tmp_path / "pyrightconfig.json"
            )  # no config file -> no-op

    def imports_from_json(this_dir: Path):
        input_stream = io.StringIO()
        old_config_path = this_dir / "pyrightconfig.json"
        with (
            pytest.raises(
                PrecommitError,
                match=re.escape(
                    f"Imported pyright configuration from {old_config_path}"
                ),
            ),
            ModifiablePyproject.load(input_stream) as pyproject,
        ):
            _merge_config_into_pyproject(pyproject, old_config_path, remove=False)

        result = input_stream.getvalue()
        expected_result = dedent("""
            [tool.pyright]
            include = ["src/**/*.py"]
            exclude = ["tests/**/*.py"]
            pythonVersion = "3.9"
            reportMissingTypeStubs = false
            reportMissingImports = true
        """)
        assert result.strip() == expected_result.strip()


def describe_update_precommit():
    def adds_pyright_hook():
        bad_config = dedent("""
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(bad_config)) as precommit,
        ):
            _update_precommit(precommit)

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
    def adds_strict_settings():
        bad_config = dedent("""
            [tool.pyright]
            include = ["**/*.py"]
            reportUnusedImport = true
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Updated pyright configuration"),
            ModifiablePyproject.load(io.StringIO(bad_config)) as pyproject,
        ):
            _update_settings(pyproject)

        result = pyproject.dumps()
        expected_result = dedent("""
            [tool.pyright]
            include = ["**/*.py"]
            reportUnusedImport = true
            typeCheckingMode = "strict"
            venv = ".venv"
            venvPath = "."
        """)
        assert result.strip() == expected_result.strip()


def describe_remove_excludes():
    def removes_exclude_key():
        config = dedent("""
            [tool.pyright]
            include = ["src"]
            exclude = ["tests"]
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Removed pyright excludes"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _remove_excludes(pyproject)
        assert "exclude" not in pyproject.get_table("tool.pyright")

    def is_noop_without_exclude():
        config = '[tool.pyright]\ninclude = ["src"]\n'
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _remove_excludes(pyproject)  # no exclude -> no-op

    def is_noop_without_pyright_table():
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _remove_excludes(pyproject)  # no tool.pyright -> no-op


def describe_update_vscode_settings():
    def recommends_pylance_when_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(PrecommitError):
            _update_vscode_settings(active=True)
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "ms-python.vscode-pylance" in extensions["recommendations"]

    def removes_pylance_when_inactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "extensions.json").write_text(
            json.dumps({"recommendations": ["ms-python.vscode-pylance"]})
        )
        with pytest.raises(PrecommitError):
            _update_vscode_settings(active=False)
        extensions = json.loads((vscode_dir / "extensions.json").read_text())
        assert "ms-python.vscode-pylance" not in extensions.get("recommendations", [])


def describe_remove_pyright():
    def removes_config_and_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyrightconfig.json").write_text("{}")
        config = dedent("""
            [project]
            name = "x"

            [tool.pyright]
            typeCheckingMode = "strict"

            [dependency-groups]
            style = ["pyright"]
        """).lstrip()
        precommit_yaml = dedent("""
            repos:
              - repo: https://github.com/ComPWA/pyright-pre-commit
                rev: v1.1.0
                hooks:
                  - id: pyright
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(precommit_yaml)) as precommit,
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _remove_pyright(precommit, pyproject)
        assert not (tmp_path / "pyrightconfig.json").exists()
        assert "tool.pyright" not in pyproject.dumps()
        assert "id: pyright" not in precommit.dumps()


def describe_main():
    def configures_vscode_when_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit:
            main(active=True, precommit=precommit)
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "ms-python.vscode-pylance" in extensions["recommendations"]
