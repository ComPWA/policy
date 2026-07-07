import re
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.cli.migrate import migrate


def _write_repo(directory: Path, args: list[str]) -> None:
    (directory / "pyproject.toml").write_text(
        dedent("""
        [project]
        name = "my-package"
        requires-python = ">=3.13"
        version = "0.0.1"
        """).lstrip()
    )
    header = dedent("""
        repos:
          - repo: https://github.com/ComPWA/policy
            rev: "0.1"
            hooks:
              - id: check-dev-files
                args:
        """).lstrip()
    rendered_args = "\n".join(f"          - {arg}" for arg in args)
    (directory / ".pre-commit-config.yaml").write_text(f"{header}{rendered_args}\n")


def describe_migrate():
    def writes_no_empty_super_tables(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        _write_repo(
            tmp_path,
            [
                "--no-cd",
                "--no-github-actions",
                "--no-cspell-update",
                "--environment-variables=A=1,B=2",
            ],
        )
        monkeypatch.chdir(tmp_path)
        migrate(Path(".pre-commit-config.yaml"))
        capsys.readouterr()
        pyproject = (tmp_path / "pyproject.toml").read_text()
        empty_section = re.compile(r"^\[[^\]]+\]\n(\[|\Z)", re.MULTILINE)
        assert empty_section.search(pyproject) is None
        assert "[tool.compwa.policy]\n" not in pyproject
        assert "[tool.compwa.policy.setup]\n" not in pyproject
        assert "[tool.compwa.policy.setup.env]" in pyproject
        assert "[tool.compwa.policy.github]" in pyproject

    def keeps_top_level_scalar_table(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        _write_repo(tmp_path, ["--repo-name=demo", "--no-cd"])
        monkeypatch.chdir(tmp_path)
        migrate(Path(".pre-commit-config.yaml"))
        capsys.readouterr()
        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert 'repo-name = "demo"' in pyproject
        assert "[tool.compwa.policy]\nrepo-name" in pyproject
