import json
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.python.ty import (
    _remove_ty,
    _update_configuration,
    _update_precommit_config,
    _update_vscode_settings,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject


def _write_pyproject(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(dedent(content).lstrip())
    return path


def _write_precommit(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".pre-commit-config.yaml"
    path.write_text(dedent(content).lstrip())
    return path


def describe_update_configuration():
    def sets_rules_and_terminal(tmp_path: Path):
        pyproject_path = _write_pyproject(tmp_path, "[project]\nname = 'x'\n")
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _update_configuration(pyproject)
        assert any("tool.ty" in m for m in pyproject.changelog)
        rules = pyproject.get_table("tool.ty.rules")
        assert rules["division-by-zero"] == "warn"
        assert pyproject.get_table("tool.ty.terminal")["error-on-warning"] is True

    def removes_default_unused_ignore_rule(tmp_path: Path):
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [tool.ty.rules]
            unused-ignore-comment = "warn"
            division-by-zero = "warn"
            possibly-missing-import = "warn"
            possibly-unresolved-reference = "warn"

            [tool.ty.terminal]
            error-on-warning = true
            """,
        )
        with ModifiablePyproject.load(pyproject_path) as pyproject:
            _update_configuration(pyproject)
        assert any("Removed tool.ty.rules" in m for m in pyproject.changelog)
        assert "unused-ignore-comment" not in pyproject.get_table("tool.ty.rules")


def describe_update_precommit_config():
    def adds_official_ty_hook(tmp_path: Path):
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
            """,
        )
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [dependency-groups]
            style = ["ty"]
            """,
        )
        with (
            ModifiablePrecommit.load(config) as precommit,
            ModifiablePyproject.load(pyproject_path) as pyproject,
        ):
            _update_precommit_config(precommit, pyproject)
        result = precommit.dumps()
        assert "https://github.com/astral-sh/ty-pre-commit" in result
        assert "id: ty" in result
        assert "args: [--no-default-groups, --group=style]" in result

    def prefers_types_group_over_style(tmp_path: Path):
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
            """,
        )
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [dependency-groups]
            style = ["ty"]
            types = ["ty"]
            typechecking = ["ty"]
            """,
        )
        with (
            ModifiablePrecommit.load(config) as precommit,
            ModifiablePyproject.load(pyproject_path) as pyproject,
        ):
            _update_precommit_config(precommit, pyproject)
        assert "args: [--no-default-groups, --group=types]" in precommit.dumps()

    def omits_args_without_matching_group(tmp_path: Path):
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
            """,
        )
        pyproject_path = _write_pyproject(tmp_path, "[project]\nname = 'x'\n")
        with (
            ModifiablePrecommit.load(config) as precommit,
            ModifiablePyproject.load(pyproject_path) as pyproject,
        ):
            _update_precommit_config(precommit, pyproject)
        assert "args:" not in precommit.dumps()

    def migrates_local_hook(tmp_path: Path):
        config = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: local
                hooks:
                  - id: ty
                    name: ty
                    entry: ty check
                    args: [--no-progress, --output-format=concise]
                    language: system
                    require_serial: true
                    types_or: [python, pyi, jupyter]
                    exclude: docs/.*
            """,
        )
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [dependency-groups]
            typechecking = ["ty"]
            """,
        )
        with (
            ModifiablePrecommit.load(config) as precommit,
            ModifiablePyproject.load(pyproject_path) as pyproject,
        ):
            _update_precommit_config(precommit, pyproject)
        result = precommit.dumps()
        assert "repo: local" not in result
        assert "https://github.com/astral-sh/ty-pre-commit" in result
        assert "entry: ty check" not in result
        assert "language: system" not in result
        assert "exclude: docs/.*" in result
        assert "args: [--no-default-groups, --group=typechecking]" in result


def describe_update_vscode_settings():
    def recommends_extension_when_active(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        _update_vscode_settings({"ty"})
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "astral-sh.ty" in extensions["recommendations"]

    def removes_extension_when_inactive(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "extensions.json").write_text(
            json.dumps({"recommendations": ["astral-sh.ty"]})
        )
        _update_vscode_settings({"mypy"})
        extensions = json.loads((vscode_dir / "extensions.json").read_text())
        assert "astral-sh.ty" not in extensions.get("recommendations", [])


def describe_remove_ty():
    def removes_config_and_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "ty.toml").write_text("")
        pyproject_path = _write_pyproject(
            tmp_path,
            """
            [project]
            name = "x"

            [tool.ty.rules]
            division-by-zero = "warn"

            [dependency-groups]
            style = ["ty"]
            """,
        )
        precommit_path = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: local
                hooks:
                  - id: ty
                    name: ty
                    entry: ty check
                    language: system
            """,
        )
        with (
            ModifiablePrecommit.load(precommit_path) as precommit,
            ModifiablePyproject.load(pyproject_path) as pyproject,
        ):
            _remove_ty(precommit, pyproject)
        assert not (tmp_path / "ty.toml").exists()
        assert "tool.ty" not in pyproject.dumps()
        assert "id: ty" not in precommit.dumps()


def describe_main():
    def configures_everything_when_selected(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(tmp_path, '[project]\nname = "x"\n')
        precommit_path = _write_precommit(tmp_path, "repos: []\n")
        with ModifiablePrecommit.load(precommit_path) as precommit:
            main({"ty"}, precommit=precommit)
        pyproject_text = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.ty.rules]" in pyproject_text
        assert "id: ty" in precommit.dumps()
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "astral-sh.ty" in extensions["recommendations"]

    def removes_ty_when_not_selected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _write_pyproject(
            tmp_path,
            '[project]\nname = "x"\n\n[tool.ty.rules]\ndivision-by-zero = "warn"\n',
        )
        precommit_path = _write_precommit(
            tmp_path,
            """
            repos:
              - repo: local
                hooks:
                  - id: ty
                    name: ty
                    entry: ty check
                    language: system
            """,
        )
        with ModifiablePrecommit.load(precommit_path) as precommit:
            main(precommit=precommit, type_checkers=set())
        assert "tool.ty" not in (tmp_path / "pyproject.toml").read_text()
        assert "id: ty" not in precommit.dumps()
