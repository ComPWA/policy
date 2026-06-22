import io
import json
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.pytest import (
    _deny_ini_options,
    _merge_coverage_into_pyproject,
    _merge_pytest_into_pyproject,
    _update_codecov_settings,
    _update_settings,
    _update_vscode_settings,
    main,
)
from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject

# cspell:ignore addopts importmode minversion numprocesses ryanluker xdist


def test_deny_ini_options_raises():
    config = dedent("""
        [tool.pytest.ini_options]
        addopts = "--color=yes"
    """).lstrip()
    with (
        ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        pytest.raises(PrecommitError, match=r"migrate to a native TOML"),
    ):
        _deny_ini_options(pyproject)


def test_deny_ini_options_sets_minversion():
    config = dedent("""
        [tool.pytest]
        addopts = "--color=yes"
    """).lstrip()
    with (
        pytest.raises(PrecommitError, match=r"minimum pytest version"),
        ModifiablePyproject.load(io.StringIO(config)) as pyproject,
    ):
        _deny_ini_options(pyproject)
    assert pyproject.get_table("tool.pytest")["minversion"] == "9.0"


def test_deny_ini_options_noop_with_minversion():
    config = dedent("""
        [tool.pytest]
        minversion = "8.0"
    """).lstrip()
    with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
        _deny_ini_options(pyproject)  # minversion present -> no-op


def test_update_settings_from_string():
    config = dedent("""
        [tool.pytest]
        addopts = "--color=no -ra"
    """).lstrip()
    with (
        pytest.raises(PrecommitError, match=r"Updated \[tool.pytest\]"),
        ModifiablePyproject.load(io.StringIO(config)) as pyproject,
    ):
        _update_settings(pyproject)
    addopts = list(pyproject.get_table("tool.pytest")["addopts"])
    assert "--color=yes" in addopts
    assert "--import-mode=importlib" in addopts
    assert "-ra" in addopts
    assert "--color=no" not in addopts


def test_update_settings_is_idempotent():
    config = dedent("""
        [tool.pytest]
        addopts = ["--color=yes", "--import-mode=importlib"]
    """).lstrip()
    with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
        _update_settings(pyproject)  # already up to date -> no error


def test_update_settings_noop_without_table():
    with ModifiablePyproject.load(io.StringIO("[project]\nname = 'x'\n")) as pyproject:
        _update_settings(pyproject)  # no [tool.pytest] -> no-op


def test_merge_pytest_into_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pytest.ini").write_text("[pytest]\nminversion = 7.0\n")
    with (
        pytest.raises(PrecommitError, match=r"Imported pytest configuration"),
        ModifiablePyproject.load(io.StringIO("[project]\nname = 'x'\n")) as pyproject,
    ):
        _merge_pytest_into_pyproject(pyproject)
    assert not (tmp_path / "pytest.ini").exists()
    assert "ini_options" in pyproject.dumps()


def test_merge_pytest_into_pyproject_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    with ModifiablePyproject.load(io.StringIO("[project]\nname = 'x'\n")) as pyproject:
        _merge_pytest_into_pyproject(pyproject)  # no pytest.ini -> no-op


def test_merge_coverage_into_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pytest.ini").write_text(
        "[coverage:run]\nbranch = True\nsource = my_pkg\n"
    )
    with (
        pytest.raises(PrecommitError, match=r"Imported Coverage.py configuration"),
        ModifiablePyproject.load(io.StringIO("[project]\nname = 'x'\n")) as pyproject,
    ):
        _merge_coverage_into_pyproject(pyproject)
    coverage = pyproject.get_table("tool.coverage.run")
    assert coverage["source"] == ["my_pkg"]


def test_merge_coverage_into_pyproject_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pytest.ini").write_text("[pytest]\nminversion = 7.0\n")
    with ModifiablePyproject.load(io.StringIO("[project]\nname = 'x'\n")) as pyproject:
        _merge_coverage_into_pyproject(pyproject)  # no [coverage:run] -> no-op


def test_update_codecov_settings():
    config = dedent("""
        [project]
        name = "x"

        [dependency-groups]
        test = ["pytest-cov"]
    """).lstrip()
    with (
        pytest.raises(PrecommitError, match=r"Updated pytest coverage settings"),
        ModifiablePyproject.load(io.StringIO(config)) as pyproject,
    ):
        _update_codecov_settings(pyproject)
    coverage = pyproject.get_table("tool.coverage.run")
    assert coverage["branch"] is True
    assert coverage["source"] == ["src"]


def test_update_codecov_settings_noop_without_coverage():
    with ModifiablePyproject.load(io.StringIO("[project]\nname = 'x'\n")) as pyproject:
        _update_codecov_settings(pyproject)  # no coverage dependency -> no-op


def test_update_vscode_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    pyproject = Pyproject.load(io.StringIO('[project]\nname = "my-package"\n'))
    with pytest.raises(PrecommitError):
        _update_vscode_settings(pyproject, coverage_gutters=True, single_threaded=False)
    settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
    assert settings["testing.showCoverageInExplorer"] is True
    extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
    assert "ryanluker.vscode-coverage-gutters" in extensions["recommendations"]


def test_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
        [project]
        name = "my-package"

        [dependency-groups]
        test = ["pytest", "pytest-cov"]

        [tool.pytest]
        addopts = "--color=no"
        """).lstrip()
    )
    with pytest.raises(PrecommitError):
        main(coverage_gutters=False, single_threaded=True)
    result = (tmp_path / "pyproject.toml").read_text()
    assert "[tool.coverage.run]" in result


def test_main_multithreaded_adds_xdist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
        [project]
        name = "my-package"

        [dependency-groups]
        test = ["pytest"]

        [tool.pytest]
        addopts = ["--color=yes", "--import-mode=importlib"]
        """).lstrip()
    )
    with pytest.raises(PrecommitError):
        main(coverage_gutters=True, single_threaded=False)
    assert "pytest-xdist" in (tmp_path / "pyproject.toml").read_text()


def test_main_without_pytest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-package"\n')
    main(coverage_gutters=False, single_threaded=True)  # no pytest dependency -> no-op
