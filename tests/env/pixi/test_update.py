from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.env.pixi._update import update_pixi_configuration
from compwa_policy.utilities.pyproject import Pyproject
from compwa_policy.utilities.session import Session


def describe_update_pixi_configuration():
    @pytest.mark.parametrize(
        "legacy_dependency", [False, True], ids=["fresh", "migration"]
    )
    def configures_quarto_without_python(
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
            "lychee": "*",
        }
        assert not config.get_table("pypi-dependencies", fallback={})
        assert "lychee" in config.get_table("tasks.linkcheck")["cmd"]
        first_result = config_path.read_text()
        assert update().changelog == []
        assert config_path.read_text() == first_result
