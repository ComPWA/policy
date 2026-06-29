import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.pyproject import (
    _convert_to_dependency_groups,
    _rename_sty_to_style,
    _update_pypi_link_names,
    _update_python_version_classifiers,
    _update_requires_python,
    main,
)
from compwa_policy.utilities.pyproject import ModifiablePyproject


def describe_update_pypi_link_names():
    def renames_known_labels():
        config = dedent("""
            [project.urls]
            Repository = "https://github.com/ComPWA/policy"
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Renamed"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _update_pypi_link_names(pyproject)
        urls = pyproject.get_table("project.urls")
        assert "Source" in urls
        assert "Repository" not in urls

    def capitalizes_lowercase_names():
        config = dedent("""
            [project.urls]
            homepage = "https://compwa.github.io"
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Capitalized"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _update_pypi_link_names(pyproject)
        assert "Homepage" in pyproject.get_table("project.urls")

    def is_noop_without_urls():
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _update_pypi_link_names(pyproject)  # no project.urls -> no-op


def describe_convert_to_dependency_groups():
    def moves_dev_groups():
        config = dedent("""
            [project]
            name = "my-package"

            [project.optional-dependencies]
            test = ["pytest"]
            viz = ["matplotlib"]
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Converted optional-dependencies"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _convert_to_dependency_groups(pyproject)
        groups = pyproject.get_table("dependency-groups")
        assert list(groups["test"]) == ["pytest"]
        optional = pyproject.get_table("project.optional-dependencies")
        assert "viz" in optional  # non-dev group kept

    def is_noop_without_optional_dependencies():
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _convert_to_dependency_groups(pyproject)  # no table -> no-op


def describe_rename_sty_to_style():
    def renames_group_and_includes():
        config = dedent("""
            [dependency-groups]
            sty = ["ruff"]
            dev = [{include-group = "sty"}]
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Renamed 'sty'"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _rename_sty_to_style(pyproject)
        groups = pyproject.get_table("dependency-groups")
        assert "style" in groups
        assert "sty" not in groups
        assert groups["dev"][0]["include-group"] == "style"

    def is_noop_without_sty():
        with ModifiablePyproject.load(
            io.StringIO("[dependency-groups]\ndev = []\n")
        ) as pyproject:
            _rename_sty_to_style(pyproject)  # no 'sty' group -> no-op


def describe_update_requires_python():
    def derives_from_python_version_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".python-version").write_text("3.12\n")
        with (
            pytest.raises(PrecommitError, match=r"requires-python"),
            ModifiablePyproject.load(
                io.StringIO("[project]\nname = 'x'\n")
            ) as pyproject,
        ):
            _update_requires_python(pyproject)
        assert pyproject.get_table("project")["requires-python"] == ">=3.12"

    def is_noop_when_already_set():
        config = dedent("""
            [project]
            name = "x"
            requires-python = ">=3.10"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_requires_python(pyproject)  # already set -> no-op


def describe_update_python_version_classifiers():
    def updates_outdated_classifiers():
        config = dedent("""
            [project]
            name = "x"
            requires-python = ">=3.12"
            classifiers = ["Programming Language :: Python :: 3.10"]
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Updated Python version classifiers"),
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
        ):
            _update_python_version_classifiers(
                pyproject, excluded_python_versions=set()
            )
        classifiers = list(pyproject.get_table("project")["classifiers"])
        assert "Programming Language :: Python :: 3.12" in classifiers
        assert "Programming Language :: Python :: 3.10" not in classifiers

    def is_noop_without_classifiers_or_tests(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)  # no tests/ dir here
        config = dedent("""
            [project]
            name = "x"
            requires-python = ">=3.12"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_python_version_classifiers(
                pyproject, excluded_python_versions=set()
            )  # no classifiers and no tests/ dir -> no-op


def describe_main():
    def runs_all_updates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            dedent("""
            [project]
            name = "my-package"
            requires-python = ">=3.12"
            classifiers = ["Programming Language :: Python :: 3.10"]
            """).lstrip()
        )
        with pytest.raises(PrecommitError):
            main(excluded_python_versions=set())
        result = (tmp_path / "pyproject.toml").read_text()
        assert "Python :: 3.12" in result

    def returns_early_without_pyproject(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        main(excluded_python_versions=set())  # no pyproject.toml -> no-op
