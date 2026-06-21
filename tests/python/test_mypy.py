import io
import json
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.mypy import (
    _merge_mypy_into_pyproject,
    _remove_mypy,
    _update_precommit_config,
    _update_vscode_settings,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject

_PRECOMMIT_WITH_MYPY = dedent("""
    repos:
      - repo: local
        hooks:
          - id: mypy
            name: mypy
            entry: mypy
            language: system
            types: [python]
""").lstrip()


def test_merge_mypy_into_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mypy.ini").write_text(
        dedent("""
        [mypy]
        ignore_missing_imports = True
        """).lstrip()
    )
    with (
        pytest.raises(PrecommitError, match=r"Imported mypy configuration"),
        ModifiablePyproject.load(io.StringIO("")) as pyproject,
    ):
        _merge_mypy_into_pyproject(pyproject)
    assert "[tool.mypy]" in pyproject.dumps()
    assert not (tmp_path / ".mypy.ini").exists()


def test_merge_mypy_into_pyproject_without_ini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    with ModifiablePyproject.load(io.StringIO("")) as pyproject:
        _merge_mypy_into_pyproject(pyproject)  # nothing to import


def test_update_precommit_config():
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
    assert "id: mypy" in result
    assert "entry: mypy" in result


def test_remove_mypy():
    pyproject_config = dedent("""
        [dependency-groups]
        style = ["mypy"]

        [tool.mypy]
        strict = true
    """).lstrip()
    with (
        pytest.raises(PrecommitError),
        ModifiablePrecommit.load(io.StringIO(_PRECOMMIT_WITH_MYPY)) as precommit,
        ModifiablePyproject.load(io.StringIO(pyproject_config)) as pyproject,
    ):
        _remove_mypy(precommit, pyproject)
    assert "mypy" not in precommit.dumps()
    assert "tool.mypy" not in pyproject.dumps()


def test_update_vscode_settings_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(PrecommitError):
        _update_vscode_settings(mypy=True)
    settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
    assert "mypy-type-checker.args" in settings


def test_update_vscode_settings_inactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(PrecommitError):
        _update_vscode_settings(mypy=False)
    extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
    assert "ms-python.mypy-type-checker" in extensions["unwantedRecommendations"]


def test_remove_mypy_without_configuration_table():
    with (
        ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit,
        ModifiablePyproject.load(io.StringIO("")) as pyproject,
    ):
        _remove_mypy(precommit, pyproject)  # no tool.mypy table to remove


def test_main_activates_mypy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    (tmp_path / "README.md").write_text("# My Package\n\nSome text.\n")
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
        main(active=True, precommit=precommit)
    assert "id: mypy" in precommit.dumps()


def test_main_deactivates_mypy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
    with (
        pytest.raises(PrecommitError),
        ModifiablePrecommit.load(io.StringIO(_PRECOMMIT_WITH_MYPY)) as precommit,
    ):
        main(active=False, precommit=precommit)
    assert "mypy" not in precommit.dumps()
