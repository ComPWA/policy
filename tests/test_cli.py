"""Tests for the Typer-based ``policy`` command-line interface."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from compwa_policy.cli._options import TypeChecker, build_arguments
from compwa_policy.cli._settings import _read_policy_config, load_settings
from compwa_policy.cli.migrate import _build_policy, _render

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)  # noqa: RUF076
def _isolate_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test in an empty directory, away from the repo's own pyproject.toml."""
    monkeypatch.chdir(tmp_path)


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


class TestBuildPolicy:
    def test_groups_into_sub_tables(self) -> None:
        policy = _build_policy([
            "--allow-labels",
            "--keep-local-precommit",
            "--no-pypi",
            "--pytest-single-threaded",
            "--repo-name=policy",
            "--repo-title=ComPWA repository policy",
            "--type-checker=ty",
        ])
        assert policy == {
            "github": {"allow-labels": True, "no-pypi": True},
            "python": {"keep-local-precommit": True, "type-checker": ["ty"]},
            "pytest-single-threaded": True,
            "repo-name": "policy",
            "repo-title": "ComPWA repository policy",
        }

    def test_repeated_list_option(self) -> None:
        policy = _build_policy(["--type-checker=mypy", "--type-checker=pyright"])
        assert policy == {"python": {"type-checker": ["mypy", "pyright"]}}

    def test_environment_variables_become_setup_env(self) -> None:
        policy = _build_policy([
            "--environment-variables=PYTHONHASHSEED=0,MPLBACKEND=agg"
        ])
        assert policy == {
            "setup": {"env": {"PYTHONHASHSEED": "0", "MPLBACKEND": "agg"}}
        }

    def test_no_python_flag(self) -> None:
        assert _build_policy(["--no-python"]) == {"python": False}
        assert _build_policy(["--python"]) == {"python": True}

    def test_round_trips_through_settings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        args = [
            "--allow-labels",
            "--no-pypi",
            "--repo-name=policy",
            "--type-checker=ty",
        ]
        policy = _build_policy(args)
        _write_policy(tmp_path, monkeypatch, _render(policy))
        settings = load_settings()
        assert settings.repo_name == "policy"
        assert settings.allow_labels is True
        assert settings.no_pypi is True
        assert settings.type_checker == ["ty"]
