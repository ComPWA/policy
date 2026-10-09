from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.env.pixi._update import update_pixi_configuration
from compwa_policy.repo.poe import check
from compwa_policy.utilities.pyproject import Pyproject
from compwa_policy.utilities.session import Session


def describe_update_pixi_configuration():
    @pytest.mark.parametrize(
        "legacy_dependency", [False, True], ids=["fresh", "existing"]
    )
    def leaves_uv_linkcheck_out_of_pixi(
        legacy_dependency: bool,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "_quarto.yml").touch()
        config_path = tmp_path / "pixi.toml"
        config_path.write_text(
            dedent("""
                [workspace]
                channels = ["conda-forge"]
                platforms = ["linux-64"]

                [dependencies]
                ffmpeg = "*"
                r-base = "*"
            """).lstrip()
            + ('\n[pypi-dependencies]\nlychee-bin = "*"\n' if legacy_dependency else "")
        )
        git_add(tmp_path)

        def update() -> Session:
            with Session() as session:
                update_pixi_configuration(
                    session,
                    is_python_package=False,
                    dev_python_version="3.12",
                    package_manager="pixi+uv",
                )
            return session

        update()
        config = Pyproject.load(config_path)
        assert config.get_table("dependencies") == {
            "ffmpeg": "*",
            "r-base": "*",
        }
        assert config.has_table("pypi-dependencies") == legacy_dependency
        if legacy_dependency:
            assert config.get_table("pypi-dependencies.lychee-bin") == "*"
        assert not config.has_table("tasks.linkcheck")
        first_result = config_path.read_text()
        assert update().changelog == []
        assert config_path.read_text() == first_result

    @pytest.mark.parametrize("task_location", [None, "tasks", "groups.doc.tasks"])
    @pytest.mark.parametrize(
        "existing_pixi", [False, True], ids=["fresh-pixi", "existing-pixi"]
    )
    def configures_quarto_linkcheck_in_poe(
        task_location: str | None,
        existing_pixi: bool,
        *,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "_quarto.yml").touch()
        (tmp_path / "index.qmd").touch()
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            dedent("""
                [dependency-groups]
                doc = []

                [tool.poe.tasks]
                doc = "quarto render"
                doclive = "quarto preview"
            """).lstrip()
            + (
                f'\n[tool.poe.{task_location}.linkcheck]\ncmd = "lychee --exclude example.org ."\nexecutor = {{ group = "doc" }}\n'
                if task_location
                else ""
            )
        )
        pixi_path = tmp_path / "pixi.toml"
        pixi_path.write_text(
            dedent("""
                [workspace]
                channels = ["conda-forge"]
                platforms = ["linux-64"]
            """).lstrip()
            + (
                '\n[tasks]\nlinkcheck = "lychee --exclude legacy.example ."\n\n[pypi-dependencies]\nlychee-bin = "*"\n'
                if existing_pixi
                else ""
            )
        )
        git_add(tmp_path)

        def update() -> None:
            with Session() as session:
                update_pixi_configuration(
                    session,
                    is_python_package=False,
                    dev_python_version="3.12",
                    package_manager="pixi+uv",
                )
                run_check(
                    check, session, has_notebooks=False, package_manager="pixi+uv"
                )

        update()
        pyproject = Pyproject.load(pyproject_path)
        location = task_location or "groups.doc.tasks"
        task = pyproject.get_table(f"tool.poe.{location}.linkcheck")
        assert task["cmd"] == (
            "lychee --exclude example.org ." if task_location else "lychee ."
        )
        assert task["executor"] == {"group": "doc"}
        assert pyproject.get_table("dependency-groups.doc") == ["lychee-bin>=0.24.0"]
        assert "qmd" in pyproject.get_table("tool.lychee")["extensions"]
        if task_location == "tasks":
            assert not pyproject.has_table("tool.poe.groups.doc.tasks.linkcheck")
        pixi = Pyproject.load(pixi_path)
        assert not pixi.has_table("dependencies.lychee")
        assert pixi.has_table("tasks.linkcheck") == existing_pixi
        assert pixi.has_table("pypi-dependencies.lychee-bin") == existing_pixi
        if existing_pixi:
            assert (
                pixi.get_table("tasks.linkcheck") == "lychee --exclude legacy.example ."
            )
            assert pixi.get_table("pypi-dependencies.lychee-bin") == "*"
        first_result = (pyproject_path.read_text(), pixi_path.read_text())
        update()
        assert (pyproject_path.read_text(), pixi_path.read_text()) == first_result
        if existing_pixi:
            with Session() as session:
                config = session.pixi
                del config.get_table("tasks")["linkcheck"]
                del config.get_table("pypi-dependencies")["lychee-bin"]
                config.dump()
            update()
            pixi = Pyproject.load(pixi_path)
            assert not pixi.has_table("tasks.linkcheck")
            assert not pixi.has_table("pypi-dependencies.lychee-bin")
            assert not pixi.has_table("dependencies.lychee")
