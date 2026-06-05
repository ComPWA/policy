"""Tests for the Typer-based ``policy`` command-line interface."""

from __future__ import annotations

import pytest

from compwa_policy.check_dev_files.cli._options import TypeChecker, build_arguments
from compwa_policy.check_dev_files.cli.migrate import _flag_group, _normalize


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
