from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
import tomlkit

from compwa_policy.repo.lychee import (
    DEFAULT_EXTENSIONS,
    check,
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

    def configures_baseline_without_tracked_quarto_files(
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
        table = Pyproject.load(path).get_table("tool.lychee")
        assert "extensions" not in table
        assert dict(table) == {
            "cache": True,
            "cache_exclude_status": "400..",
            "hidden": True,
            "include_fragments": "anchor-only",
            "include_verbatim": True,
            "max_cache_age": "7d",
        }

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


def describe_check():
    @pytest.mark.parametrize(
        ("filename", "header", "task"),
        [
            ("pyproject.toml", "tool.poe.tasks", 'linkcheck = "lychee ."'),
            (
                "pyproject.toml",
                "tool.poe.groups.doc.tasks.linkcheck",
                'cmd = ["uvx", "lychee@0.24", "."]',
            ),
            (
                "pyproject.toml",
                "tool.poe.tasks.linkcheck",
                'shell = "uvx --from lychee-bin lychee ."',
            ),
            ("pyproject.toml", "tool.pixi.tasks", 'linkcheck = "lychee ."'),
            (
                "pyproject.toml",
                "tool.pixi.feature.dev.tasks.linkcheck",
                'cmd = "lychee ."',
            ),
            ("pixi.toml", "tasks", 'linkcheck = "lychee ."'),
            ("pixi.toml", "feature.dev.tasks.linkcheck", 'cmd = "lychee ."'),
        ],
        ids=[
            "poe",
            "poe-group",
            "poe-shell",
            "pixi",
            "pixi-feature",
            "standalone-pixi",
            "standalone-pixi-feature",
        ],
    )
    def configures_existing_lychee_tasks_without_rewriting_them(
        filename: str,
        header: str,
        task: str,
        *,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        run_check: Callable[..., None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        path = tmp_path / filename
        path.write_text(
            dedent(f"""\
            [{header}]
            {task}
            """)
        )
        with Session() as session:
            run_check(check, session)
        result = tomlkit.loads(path.read_text())
        config_path = path if filename == "pyproject.toml" else tmp_path / "lychee.toml"
        table = tomlkit.loads(config_path.read_text())
        if filename == "pyproject.toml":
            table = table["tool"]["lychee"]
        assert table["max_cache_age"] == "7d"
        assert table["cache_exclude_status"] == "400.."
        assert "max_redirects" not in table
        original = tomlkit.loads(
            dedent(f"""\
            [{header}]
            {task}
            """)
        )
        for key in header.split("."):
            result = result[key]
            original = original[key]
        assert result == original
        contents = config_path.read_text()
        with Session() as session:
            run_check(check, session)
            assert not session.collect_changes()
        assert config_path.read_text() == contents

    @pytest.mark.parametrize("standalone", [False, True])
    def enforces_baseline_and_preserves_repository_options(
        standalone: bool,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        run_check: Callable[..., None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        path = tmp_path / ("lychee.toml" if standalone else "pyproject.toml")
        header = "" if standalone else "[tool.lychee]"
        path.write_text(
            dedent(f"""\
            {header}
            cache = false
            hidden = false
            include_fragments = "none"
            include_verbatim = false
            max_cache_age = "2d"
            cache_exclude_status = "500.."
            exclude = ["example.org"]
            exclude_path = ["tests"]
            remap = ['^git\\+(https://.*)$ $1']
            extensions = ["md", "typ"]
            timeout = 60
            """)
        )
        with Session() as session:
            run_check(check, session)
        table: Any = tomlkit.loads(path.read_text())
        if not standalone:
            table = table["tool"]["lychee"]
        assert table["cache"] is True
        assert table["hidden"] is True
        assert table["include_fragments"] == "anchor-only"
        assert table["include_verbatim"] is True
        assert table["max_cache_age"] == "7d"
        assert table["cache_exclude_status"] == "400.."
        assert table["exclude"] == ["example.org"]
        assert table["exclude_path"] == ["tests"]
        assert len(table["remap"]) == 1
        assert table["extensions"] == ["md", "typ"]
        assert table["timeout"] == 60
        assert not (tmp_path / "pixi.toml").exists()

    def preserves_sphinx_linkcheck(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        run_check: Callable[..., None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "pyproject.toml"
        content = dedent("""\
            [tool.poe.tasks]
            linkcheck = "sphinx-build -b linkcheck docs docs/_build/linkcheck"
            """)
        path.write_text(content)
        with Session() as session:
            run_check(check, session)
            assert not session.collect_changes()
        assert path.read_text() == content
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
