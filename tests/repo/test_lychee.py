from collections.abc import Callable
from pathlib import Path

import pytest
import tomlkit

from compwa_policy.repo.lychee import (
    DEFAULT_EXTENSIONS,
    configure_lychee,
    require_lychee,
)
from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject
from compwa_policy.utilities.session import Session


def describe_configure_lychee():
    @pytest.mark.parametrize(
        "standalone", [False, True], ids=["pyproject", "standalone"]
    )
    @pytest.mark.parametrize("custom", [False, True], ids=["defaults", "custom"])
    def adds_missing_extensions_and_preserves_options(
        standalone: bool,
        custom: bool,
        *,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "index.qmd").touch()
        path = tmp_path / ("lychee.toml" if standalone else "pyproject.toml")
        header = "" if standalone else "[tool.lychee]\n"
        path.write_text(
            header
            + (
                'extensions = ["md", "typ"]\nexclude = ["example.org"]\n'
                if custom
                else ""
            )
        )
        git_add(tmp_path)
        config_path = tmp_path / "pixi.toml" if standalone else path
        if standalone:
            config_path.touch()
        with ModifiablePyproject.load(config_path) as config:
            configure_lychee(config)
        result = Pyproject.load(path)
        table = (
            tomlkit.loads(path.read_text())
            if standalone
            else result.get_table("tool.lychee")
        )
        assert list(table["extensions"]) == [
            *(["md", "typ"] if custom else DEFAULT_EXTENSIONS),
            "qmd",
        ]
        assert "root_dir" not in table
        if custom:
            assert table["exclude"] == ["example.org"]
        original = path.read_text()
        with ModifiablePyproject.load(config_path) as config:
            configure_lychee(config)
        assert path.read_text() == original

    def leaves_configuration_unchanged_without_tracked_quarto_files(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "untracked.qmd").touch()
        path = tmp_path / "pyproject.toml"
        path.touch()
        with ModifiablePyproject.load(path) as config:
            configure_lychee(config)
        assert not path.read_text()

    def uses_session_pyproject_for_separate_pixi_config(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "index.qmd").touch()
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "pixi.toml").touch()
        git_add(tmp_path)
        with Session() as session:
            configure_lychee(session.pixi, session)
        assert (
            "qmd"
            in Pyproject.load(tmp_path / "pyproject.toml").get_table("tool.lychee")[
                "extensions"
            ]
        )
        assert not (tmp_path / "lychee.toml").exists()


def describe_require_lychee():
    @pytest.mark.parametrize(
        ("dependency", "expected"),
        [
            ("lychee-bin", "lychee-bin>=0.24.0"),
            ("lychee-bin>=0.24.0", "lychee-bin>=0.24.0"),
            ("lychee-bin>=0.25", "lychee-bin>=0.25"),
            ("lychee-bin>=0.20,<1", "lychee-bin<1,>=0.20,>=0.24.0"),
        ],
    )
    def updates_included_group(dependency: str, expected: str, tmp_path: Path):
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[dependency-groups]\ndoc = [{include-group = "linkcheck"}]\nlinkcheck = ["'
            + dependency
            + '"]\n'
        )
        with ModifiablePyproject.load(path) as config:
            require_lychee(config, "doc")
        result = Pyproject.load(path)
        assert result.get_table("dependency-groups.linkcheck") == [expected]
        assert result.get_table("dependency-groups.doc") == [
            {"include-group": "linkcheck"}
        ]
