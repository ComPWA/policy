import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.python.black import (
    _remove_outdated_settings,
    _update_black_settings,
    _update_precommit_repo,
    main,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.session import Session


def describe_remove_outdated_settings():
    def removes_line_length():
        config = dedent("""
            [tool.black]
            line-length = 88
            preview = true
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _remove_outdated_settings(pyproject)
        assert any("Removed line-length" in m for m in pyproject.changelog)
        assert "line-length" not in pyproject.dumps()

    def keeps_other_options():
        config = dedent("""
            [tool.black]
            preview = true
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _remove_outdated_settings(pyproject)
        assert "preview = true" in pyproject.dumps()


def describe_update_black_settings():
    def drops_target_version_with_requires_python():
        config = dedent("""
            [project]
            requires-python = ">=3.10"

            [tool.black]
            target-version = ["py39"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_black_settings(pyproject)
        assert pyproject.changelog  # something changed
        result = pyproject.dumps()
        assert "target-version" not in result
        assert "preview = true" in result

    def enables_preview_without_target_version():
        config = dedent("""
            [project]
            requires-python = ">=3.10"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_black_settings(pyproject)
        assert any("Updated black configuration" in m for m in pyproject.changelog)
        result = pyproject.dumps()
        assert "preview = true" in result
        assert "target-version" not in result

    def derives_target_version_from_classifiers():
        config = dedent("""
            [project]
            classifiers = [
                "Programming Language :: Python :: 3.10",
                "Programming Language :: Python :: 3.11",
            ]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_black_settings(pyproject)
        assert any("Updated black configuration" in m for m in pyproject.changelog)
        result = pyproject.dumps()
        assert '"py310"' in result
        assert '"py311"' in result

    def is_noop_when_already_compliant():
        config = dedent("""
            [project]
            requires-python = ">=3.10"

            [tool.black]
            preview = true
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_black_settings(pyproject)  # already compliant -> no change
        assert "preview = true" in pyproject.dumps()


def describe_update_precommit_repo():
    @pytest.mark.parametrize("has_notebooks", [False, True])
    def replaces_with_mirror(has_notebooks: bool):
        config = dedent("""
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
        """).lstrip()
        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            _update_precommit_repo(precommit, has_notebooks)
        assert precommit.changelog  # something changed
        result = precommit.dumps()
        assert "https://github.com/psf/black-pre-commit-mirror" in result
        assert ("black-jupyter" in result) is has_notebooks


def describe_main():
    def is_noop_without_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        precommit = ModifiablePrecommit.load(io.StringIO("repos: []\n"))
        with Session.load(precommit) as session:
            main(session, has_notebooks=False)  # no pyproject.toml -> no-op

    def replaces_black_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            dedent("""
            [project]
            requires-python = ">=3.10"

            [tool.black]
            line-length = 88
            """).lstrip()
        )
        config = dedent("""
            repos:
              - repo: https://github.com/psf/black
                rev: 24.4.2
                hooks:
                  - id: black
        """).lstrip()
        precommit = ModifiablePrecommit.load(io.StringIO(config))
        with Session.load(precommit) as session:
            main(session, has_notebooks=False)
        result = precommit.dumps()
        assert "https://github.com/psf/black\n" not in result
        assert "https://github.com/psf/black-pre-commit-mirror" in result
