from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.env import direnv
from compwa_policy.utilities.session import Session


def describe_check():
    @pytest.mark.parametrize(
        ("pyproject", "expected_sync"),
        [
            (
                dedent("""
                    [project]
                    name = "my-package"
                """),
                "uv sync --quiet",
            ),
            (
                dedent("""
                    [project]
                    name = "my-package"

                    [project.optional-dependencies]
                """),
                "uv sync --quiet",
            ),
            (
                dedent("""
                    [project]
                    name = "my-package"

                    [project.optional-dependencies]
                    viz = ["matplotlib"]
                """),
                "uv sync --all-extras --quiet",
            ),
        ],
        ids=["no-table", "empty-table", "with-extras"],
    )
    def adds_all_extras_only_with_extras(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run_check,
        pyproject: str,
        expected_sync: str,
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(pyproject)
        with Session() as session:
            run_check(direnv.check, session, package_manager="uv")
        envrc = (tmp_path / ".envrc").read_text()
        assert envrc.startswith(f"{expected_sync}\n")
