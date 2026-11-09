from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.env import direnv
from compwa_policy.utilities.session import Session


def describe_check():
    @pytest.mark.parametrize(
        ("pyproject", "expected_layout"),
        [
            (
                dedent("""
                    [project]
                    name = "my-package"
                """),
                "layout uv --quiet",
            ),
            (
                dedent("""
                    [project]
                    name = "my-package"

                    [project.optional-dependencies]
                """),
                "layout uv --quiet",
            ),
            (
                dedent("""
                    [project]
                    name = "my-package"

                    [project.optional-dependencies]
                    viz = ["matplotlib"]
                """),
                "layout uv --all-extras --quiet",
            ),
        ],
        ids=["no-table", "empty-table", "with-extras"],
    )
    @pytest.mark.parametrize("package_manager", ["uv", "pixi+uv"])
    @pytest.mark.parametrize(
        "tracked_lock", [False, True], ids=["untracked", "tracked"]
    )
    def adds_all_extras_only_with_extras(
        *,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run_check,
        git_init,
        git_add,
        pyproject: str,
        expected_layout: str,
        package_manager: str,
        tracked_lock: bool,
    ):
        monkeypatch.chdir(tmp_path)
        git_init(tmp_path)
        (tmp_path / "pyproject.toml").write_text(pyproject)
        (tmp_path / "uv.lock").touch()
        if tracked_lock:
            git_add(tmp_path)
        with Session() as session:
            run_check(
                direnv.check,
                session,
                package_manager=package_manager,
                environment_variables={"EXAMPLE": "value"},
            )
        envrc = (tmp_path / ".envrc").read_text()
        expected_lines = []
        if package_manager == "pixi+uv":
            expected_lines.extend([
                "watch_file pixi.lock",
                'eval "$(pixi shell-hook)"',
            ])
        if not tracked_lock:
            expected_lines.append("uv lock --quiet")
        expected_lines.extend([expected_layout, "export EXAMPLE=value"])
        assert envrc.splitlines() == expected_lines

    @pytest.mark.parametrize(
        ("environment", "expected_flag"),
        [
            ("dev", " --environment dev"),
            ("my-package", " --environment my-package"),
            ("default", ""),
        ],
    )
    def keeps_pixi_shell_hook(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        run_check,
        environment: str,
        expected_flag: str,
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            dedent(f"""
            [project]
            name = "my-package"

            [tool.pixi.environments]
            {environment} = []
        """)
        )
        with Session() as session:
            run_check(direnv.check, session, package_manager="pixi")
        assert (tmp_path / ".envrc").read_text() == dedent(f"""\
            watch_file pixi.lock
            eval "$(pixi shell-hook{expected_flag})"
        """)
