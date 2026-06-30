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

# cspell:ignore minversion ryanluker xdist


def describe_deny_ini_options():
    def raises_on_ini_options():
        config = dedent("""
            [tool.pytest.ini_options]
            addopts = "--color=yes"
        """).lstrip()
        with (
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
            pytest.raises(PrecommitError, match=r"migrate to a native TOML"),
        ):
            _deny_ini_options(pyproject)

    def sets_minversion():
        config = dedent("""
            [tool.pytest]
            addopts = "--color=yes"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _deny_ini_options(pyproject)
        assert any("minimum pytest version" in m for m in pyproject.changelog)
        assert pyproject.get_table("tool.pytest")["minversion"] == "9.0"

    def is_noop_with_minversion():
        config = dedent("""
            [tool.pytest]
            minversion = "8.0"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _deny_ini_options(pyproject)  # minversion present -> no-op

    def ignores_missing_pytest_table():
        config = dedent("""
            [project]
            name = "my-package"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _deny_ini_options(pyproject)
            assert pyproject.changelog == []


def describe_update_settings():
    def updates_from_string():
        config = dedent("""
            [tool.pytest]
            addopts = "--color=no -ra"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_settings(pyproject)
        assert any("Updated [tool.pytest]" in m for m in pyproject.changelog)
        addopts = list(pyproject.get_table("tool.pytest")["addopts"])
        assert "--color=yes" in addopts
        assert "--import-mode=importlib" in addopts
        assert "-ra" in addopts
        assert "--color=no" not in addopts

    def is_idempotent():
        config = dedent("""
            [tool.pytest]
            addopts = ["--color=yes", "--import-mode=importlib"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_settings(pyproject)  # already up to date -> no error

    def is_noop_without_table():
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _update_settings(pyproject)  # no [tool.pytest] -> no-op


def describe_merge_pytest_into_pyproject():
    def imports_and_removes_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pytest.ini").write_text("[pytest]\nminversion = 7.0\n")
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_pytest_into_pyproject(pyproject)
        assert any("Imported pytest configuration" in m for m in pyproject.changelog)
        assert not (tmp_path / "pytest.ini").exists()
        assert "ini_options" in pyproject.dumps()

    def is_noop_without_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_pytest_into_pyproject(pyproject)  # no pytest.ini -> no-op


def describe_merge_coverage_into_pyproject():
    def imports_coverage_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pytest.ini").write_text(
            "[coverage:run]\nbranch = True\nsource = my_pkg\n"
        )
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_coverage_into_pyproject(pyproject)
        assert any(
            "Imported Coverage.py configuration" in m for m in pyproject.changelog
        )
        coverage = pyproject.get_table("tool.coverage.run")
        assert coverage["source"] == ["my_pkg"]

    def is_noop_without_coverage_section(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pytest.ini").write_text("[pytest]\nminversion = 7.0\n")
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_coverage_into_pyproject(pyproject)  # no [coverage:run] -> no-op


def describe_update_codecov_settings():
    def sets_branch_and_source():
        config = dedent("""
            [project]
            name = "x"

            [dependency-groups]
            test = ["pytest-cov"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_codecov_settings(pyproject)
        assert any("Updated pytest coverage settings" in m for m in pyproject.changelog)
        coverage = pyproject.get_table("tool.coverage.run")
        assert coverage["branch"] is True
        assert coverage["source"] == ["src"]

    def can_disable_branch_coverage():
        config = dedent("""
            [project]
            name = "x"

            [dependency-groups]
            test = ["pytest-cov"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_codecov_settings(pyproject, branch_coverage=False)
        assert any("Updated pytest coverage settings" in m for m in pyproject.changelog)
        coverage = pyproject.get_table("tool.coverage.run")
        assert coverage["branch"] is False

    def is_noop_without_coverage():
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _update_codecov_settings(pyproject)  # no coverage dependency -> no-op


def describe_update_vscode_settings():
    def enables_coverage_gutters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        pyproject = Pyproject.load(io.StringIO('[project]\nname = "my-package"\n'))
        _update_vscode_settings(pyproject, coverage_gutters=True, single_threaded=False)
        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
        assert settings["testing.showCoverageInExplorer"] is True
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "ryanluker.vscode-coverage-gutters" in extensions["recommendations"]


def describe_main():
    def writes_coverage_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
        main(coverage_gutters=False, single_threaded=True)
        result = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.coverage.run]" in result

    def adds_xdist_when_multithreaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
        main(coverage_gutters=True, single_threaded=False)
        assert "pytest-xdist" in (tmp_path / "pyproject.toml").read_text()

    def is_noop_without_pytest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-package"\n')
        main(coverage_gutters=False, single_threaded=True)  # no pytest dep -> no-op
