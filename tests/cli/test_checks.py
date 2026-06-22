import subprocess  # noqa: S404
from pathlib import Path
from textwrap import dedent

import pytest
import typer

from compwa_policy.cli._checks import (
    ALL_GROUPS,
    check_dev_python_version,
    compute_context,
    dispatch,
    run_all,
)
from compwa_policy.cli._options import build_arguments

# cspell:ignore capsys classifiers pyproject

_PYPROJECT = dedent("""
    [project]
    name = "my-package"
    classifiers = [
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ]
""").lstrip()


def _git_commit(directory: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=directory, check=True)  # noqa: S607
    subprocess.run(["git", "add", "-A"], cwd=directory, check=True)  # noqa: S607
    git_author = ["-c", "user.name=t", "-c", "user.email=t@t"]
    commit = ["git", *git_author, "commit", "-qm", "init", "--allow-empty"]
    subprocess.run(commit, cwd=directory, check=True)  # noqa: S603


def describe_check_dev_python_version():
    def passes_without_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        args = build_arguments(dev_python_version="3.12")
        assert check_dev_python_version(args) == 0

    def passes_for_supported_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT)
        args = build_arguments(dev_python_version="3.12")
        assert check_dev_python_version(args) == 0

    def fails_for_unsupported_version(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT)
        args = build_arguments(dev_python_version="3.9")
        assert check_dev_python_version(args) == 1
        assert "not listed in the supported Python versions" in capsys.readouterr().out


def describe_compute_context():
    def detects_python_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("x = 1\n")
        _git_commit(tmp_path)
        monkeypatch.chdir(tmp_path)
        args = build_arguments(dev_python_version="3.12")
        ctx = compute_context(args)
        assert ctx.is_python_repo is True
        assert ctx.has_notebooks is False

    def respects_explicit_python_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _git_commit(tmp_path)
        monkeypatch.chdir(tmp_path)
        args = build_arguments(dev_python_version="3.12", python=False)
        ctx = compute_context(args)
        assert ctx.is_python_repo is False


def describe_all_groups():
    def covers_every_subcommand_group():
        assert (
            frozenset({"python", "github", "env", "nb", "format", "repo"}) == ALL_GROUPS
        )


def _runnable_repo(directory: Path) -> None:
    (directory / ".pre-commit-config.yaml").write_text("repos: []\n")
    (directory / "pyproject.toml").write_text(
        '[project]\nname = "x"\nrequires-python = ">=3.12"\n'
    )
    (directory / "src" / "x").mkdir(parents=True)
    (directory / "src" / "x" / "module.py").write_text("x = 1\n")
    _git_commit(directory)


def describe_run_all():
    def applies_changes_and_returns_one(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        _runnable_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        args = build_arguments(dev_python_version="3.12", package_manager="uv")
        assert run_all(args) == 1  # pristine repo needs updates
        capsys.readouterr()


def describe_dispatch():
    def raises_typer_exit(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        _runnable_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        args = build_arguments(dev_python_version="3.12", package_manager="uv")
        with pytest.raises(typer.Exit):
            dispatch(args, "env")
        capsys.readouterr()
