import io
import json
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.ty import (
    _remove_ty,
    _update_configuration,
    _update_precommit_config,
    _update_vscode_settings,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject


def describe_update_configuration():
    def sets_rules_and_terminal():
        with (
            pytest.raises(PrecommitError, match=r"tool.ty"),
            ModifiablePyproject.load(
                io.StringIO("[project]\nname = 'x'\n")
            ) as pyproject,
        ):
            _update_configuration(pyproject)
        rules = pyproject.get_table("tool.ty.rules")
        assert rules["division-by-zero"] == "warn"
        assert pyproject.get_table("tool.ty.terminal")["error-on-warning"] is True

    def removes_default_unused_ignore_rule():
        config = dedent("""
            [tool.ty.rules]
            unused-ignore-comment = "warn"
            division-by-zero = "warn"
            possibly-missing-import = "warn"
            possibly-unresolved-reference = "warn"

            [tool.ty.terminal]
            error-on-warning = true
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Removed tool.ty.rules"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _update_configuration(pyproject)
        assert "unused-ignore-comment" not in pyproject.get_table("tool.ty.rules")


def describe_update_precommit_config():
    def adds_local_ty_hook():
        config = dedent("""
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(config)) as precommit,
        ):
            _update_precommit_config(precommit)
        result = precommit.dumps()
        assert "repo: local" in result
        assert "id: ty" in result

    def preserves_existing_exclude():
        config = dedent("""
            repos:
              - repo: local
                hooks:
                  - id: ty
                    name: ty
                    entry: ty check
                    language: system
                    exclude: ^docs/
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(config)) as precommit,
        ):
            _update_precommit_config(precommit)
        assert "exclude: ^docs/" in precommit.dumps()


def describe_update_vscode_settings():
    def recommends_extension_when_active(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(PrecommitError):
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
        with pytest.raises(PrecommitError):
            _update_vscode_settings({"mypy"})
        extensions = json.loads((vscode_dir / "extensions.json").read_text())
        assert "astral-sh.ty" not in extensions.get("recommendations", [])


def describe_remove_ty():
    def removes_config_and_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "ty.toml").write_text("")
        config = dedent("""
            [project]
            name = "x"

            [tool.ty.rules]
            division-by-zero = "warn"

            [dependency-groups]
            style = ["ty"]
        """).lstrip()
        precommit_yaml = dedent("""
            repos:
              - repo: local
                hooks:
                  - id: ty
                    name: ty
                    entry: ty check
                    language: system
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(precommit_yaml)) as precommit,
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
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
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit,
        ):
            main({"ty"}, keep_precommit=False, precommit=precommit)
        # All steps are applied in a single pass (no per-step short-circuit).
        pyproject_text = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.ty.rules]" in pyproject_text
        assert "id: ty" in precommit.dumps()
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "astral-sh.ty" in extensions["recommendations"]

    def removes_ty_when_not_selected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\n\n[tool.ty.rules]\ndivision-by-zero = "warn"\n'
        )
        precommit_yaml = dedent("""
            repos:
              - repo: local
                hooks:
                  - id: ty
                    name: ty
                    entry: ty check
                    language: system
        """).lstrip()
        with (
            pytest.raises(PrecommitError),
            ModifiablePrecommit.load(io.StringIO(precommit_yaml)) as precommit,
        ):
            main(set(), keep_precommit=False, precommit=precommit)
        assert "tool.ty" not in (tmp_path / "pyproject.toml").read_text()
        assert "id: ty" not in precommit.dumps()
