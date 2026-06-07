"""Tests for the Typer-based ``policy`` command-line interface."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from compwa_policy.check_dev_files.cli._options import TypeChecker, build_arguments
from compwa_policy.check_dev_files.cli._settings import (
    _read_policy_config,
    load_settings,
)
from compwa_policy.check_dev_files.cli.migrate import _flag_group, _normalize

if TYPE_CHECKING:
    from pathlib import Path


def test_build_arguments_defaults() -> None:
    args = build_arguments()
    assert args.dev_python_version == "3.13"
    assert args.package_manager == "uv"
    assert args.repo_organization == "ComPWA"
    assert args.type_checker == set()
    assert args.excluded_python_versions == set()
    assert args.keep_workflow == set()
    assert args.python is None


def test_build_arguments_post_processing() -> None:
    # cspell:ignore myproj
    args = build_arguments(
        type_checker=[TypeChecker.mypy, TypeChecker.ty],
        excluded_python_versions="3.6, 3.7",
        macos_python_version="disable",
        repo_name="myproj",
    )
    assert args.type_checker == {"mypy", "ty"}
    assert args.excluded_python_versions == {"3.6", "3.7"}
    assert args.macos_python_version is None
    assert args.repo_name == "myproj"
    assert args.repo_title == "myproj"  # falls back to repo_name


def _write_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, table: str) -> None:
    (tmp_path / "pyproject.toml").write_text(dedent(table))
    monkeypatch.chdir(tmp_path)


class TestPyprojectConfig:
    def test_no_table_is_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(tmp_path, monkeypatch, '[project]\nname = "x"\n')
        assert _read_policy_config() == {}

    def test_flatten_nested_tables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            dev-python-version = "3.12"
            package-manager = "pixi"

            [tool.compwa.policy.python]
            imports-on-top = true
            type-checker = ["mypy", "pyright"]

            [tool.compwa.policy.nb]
            no-binder = true

            [tool.compwa.policy.setup]
            keep-contributing-md = true

            [tool.compwa.policy.setup.env]
            PYTHONHASHSEED = "0"
            MPLBACKEND = "agg"
            """,
        )
        assert _read_policy_config() == {
            "dev_python_version": "3.12",
            "package_manager": "pixi",
            "imports_on_top": True,
            "type_checker": ["mypy", "pyright"],
            "no_binder": True,
            "keep_contributing_md": True,
            "environment_variables": {
                "PYTHONHASHSEED": "0",
                "MPLBACKEND": "agg",
            },
        }

    def test_pyproject_overrides_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            dev-python-version = "3.12"

            [tool.compwa.policy.python]
            type-checker = ["mypy", "pyright"]

            [tool.compwa.policy.setup.env]
            PYTHONHASHSEED = "0"
            """,
        )
        args = build_arguments()
        assert args.dev_python_version == "3.12"
        assert args.type_checker == {"mypy", "pyright"}
        assert args.environment_variables == "PYTHONHASHSEED=0"

    def test_cli_overrides_pyproject(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            dev-python-version = "3.12"
            """,
        )
        assert load_settings(dev_python_version="3.11").dev_python_version == "3.11"
        assert load_settings(dev_python_version=None).dev_python_version == "3.12"

    def test_unknown_option_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            does-not-exist = true
            """,
        )
        with pytest.raises(ValueError, match="does_not_exist"):
            load_settings()


def test_normalize_is_idempotent() -> None:
    args = ["--no-pypi", "--allow-labels", "--keep-workflow=a"]
    normalized = _normalize(args)
    assert normalized == ["--allow-labels", "--keep-workflow=a", "--no-pypi"]
    assert _normalize(normalized) == normalized


@pytest.mark.parametrize(
    ("flag", "group"),
    [
        ("--no-ruff", "python"),
        ("--no-pypi", "github"),
        ("--package-manager", "env"),
        ("--no-binder", "nb"),
        ("--no-cspell-update", "format"),
        ("--gitpod", "repo"),
        ("--repo-name", "shared"),
        ("--does-not-exist", "unknown"),
    ],
)
def test_flag_group(flag: str, group: str) -> None:
    assert _flag_group(flag) == group
