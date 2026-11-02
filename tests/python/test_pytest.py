import io
import json
from pathlib import Path
from textwrap import dedent

import pytest
import tomli
import yaml

from compwa_policy.errors import PolicyError
from compwa_policy.python.pytest import (
    _deny_ini_options,
    _merge_coverage_into_pyproject,
    _merge_pytest_into_pyproject,
    _migrate_coverage_threshold,
    _update_codecov_settings,
    _update_settings,
    _update_vscode_settings,
    check,
)
from compwa_policy.utilities.pyproject import ModifiablePyproject
from compwa_policy.utilities.session import Session

# cspell:ignore minversion ryanluker xdist


def describe_deny_ini_options():
    def raises_on_ini_options():
        config = dedent("""
            [tool.pytest.ini_options]
            addopts = "--color=yes"
        """).lstrip()
        with (
            ModifiablePyproject.load(io.StringIO(config)) as pyproject,
            pytest.raises(PolicyError, match=r"migrate to a native TOML"),
        ):
            _deny_ini_options(pyproject)

    def sets_minversion():
        config = dedent("""
            [tool.pytest]
            addopts = "--color=yes"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _deny_ini_options(pyproject)
        assert any("minimum pytest version" in m for m in pyproject.changelog)
        assert pyproject.get_table("tool.pytest")["minversion"] == "9.0"

    def is_noop_with_minversion():
        config = dedent("""
            [tool.pytest]
            minversion = "8.0"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _deny_ini_options(pyproject)  # minversion present -> no-op

    def ignores_missing_pytest_table():
        config = dedent("""
            [project]
            name = "my-package"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _deny_ini_options(pyproject)
            assert pyproject.changelog == []


def describe_update_settings():
    def updates_from_string():
        config = dedent("""
            [tool.pytest]
            addopts = "--color=no -ra"
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_settings(pyproject)
        assert any("Updated [tool.pytest]" in m for m in pyproject.changelog)
        addopts = list(pyproject.get_table("tool.pytest")["addopts"])
        assert "--color=yes" in addopts
        assert "--import-mode=importlib" in addopts
        assert "-ra" in addopts
        assert "--color=no" not in addopts

    def is_idempotent():
        config = dedent("""
            [tool.pytest]
            addopts = ["--color=yes", "--import-mode=importlib"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_settings(pyproject)  # already up to date -> no error

    def is_noop_without_table():
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _update_settings(pyproject)  # no [tool.pytest] -> no-op


def describe_merge_pytest_into_pyproject():
    def imports_and_removes_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pytest.ini").write_text("[pytest]\nminversion = 7.0\n")
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_pytest_into_pyproject(pyproject)
        assert any("Imported pytest configuration" in m for m in pyproject.changelog)
        assert not (tmp_path / "pytest.ini").exists()
        assert "ini_options" in pyproject.dumps()

    def is_noop_without_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_pytest_into_pyproject(pyproject)  # no pytest.ini -> no-op


def describe_merge_coverage_into_pyproject():
    def imports_coverage_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pytest.ini").write_text(
            "[coverage:run]\nbranch = True\nsource = my_pkg\n"
        )
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_coverage_into_pyproject(pyproject)
        assert any(
            "Imported Coverage.py configuration" in m for m in pyproject.changelog
        )
        coverage = pyproject.get_table("tool.coverage.run")
        assert coverage["source"] == ["my_pkg"]

    def is_noop_without_coverage_section(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pytest.ini").write_text("[pytest]\nminversion = 7.0\n")
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _merge_coverage_into_pyproject(pyproject)  # no [coverage:run] -> no-op


def describe_update_codecov_settings():
    def sets_branch_and_source():
        config = dedent("""
            [project]
            name = "x"

            [dependency-groups]
            test = ["pytest-cov"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_codecov_settings(pyproject)
        assert any("Updated pytest coverage settings" in m for m in pyproject.changelog)
        coverage = pyproject.get_table("tool.coverage.run")
        assert coverage["branch"] is True
        assert coverage["source"] == ["src"]

    def can_disable_branch_coverage():
        config = dedent("""
            [project]
            name = "x"

            [dependency-groups]
            test = ["pytest-cov"]
        """).lstrip()
        with ModifiablePyproject.load(io.StringIO(config)) as pyproject:
            _update_codecov_settings(pyproject, branch_coverage=False)
        assert any("Updated pytest coverage settings" in m for m in pyproject.changelog)
        coverage = pyproject.get_table("tool.coverage.run")
        assert coverage["branch"] is False

    def is_noop_without_coverage():
        with ModifiablePyproject.load(
            io.StringIO("[project]\nname = 'x'\n")
        ) as pyproject:
            _update_codecov_settings(pyproject)  # no coverage dependency -> no-op


def describe_update_vscode_settings():
    def enables_coverage_gutters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        pyproject = ModifiablePyproject.load(
            io.StringIO('[project]\nname = "my-package"\n')
        )
        with Session(pyproject=pyproject) as session:
            _update_vscode_settings(
                session,
                coverage_gutters=True,
                single_threaded=False,
            )
        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
        assert settings["testing.showCoverageInExplorer"] is True
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "ryanluker.vscode-coverage-gutters" in extensions["recommendations"]


def describe_main():
    def writes_coverage_config(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_check
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            dedent("""
            [project]
            name = "my-package"

            [dependency-groups]
            test = ["pytest", "pytest-cov"]

            [tool.pytest]
            addopts = "--color=no"

            [tool.poe.tasks]
            cov = "pytest --cov=my_package --cov-fail-under=95"
            """).lstrip()
        )
        (tmp_path / "codecov.yml").write_text(
            "coverage:\n  status:\n    project:\n      default:\n        target: 90%\n"
        )
        with Session.load() as session:
            run_check(
                check,
                session,
                allow_vscode_coverage_gutters=False,
                pytest_single_threaded=True,
            )
        result = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.coverage.run]" in result
        assert tomli.loads(result)["tool"]["coverage"]["report"]["fail_under"] == 90
        codecov = yaml.safe_load((tmp_path / "codecov.yml").read_text())
        assert codecov["coverage"]["status"]["project"]["default"] == {}

    def adds_xdist_when_multithreaded(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_check
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            dedent("""
            [project]
            name = "my-package"

            [dependency-groups]
            test = ["pytest"]

            [tool.pytest]
            addopts = ["--color=yes", "--import-mode=importlib"]
            """).lstrip()
        )
        with Session.load() as session:
            run_check(
                check,
                session,
                allow_vscode_coverage_gutters=True,
                pytest_single_threaded=False,
            )
        assert "pytest-xdist" in (tmp_path / "pyproject.toml").read_text()

    def is_noop_without_pytest(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_check
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-package"\n')
        with Session.load() as session:
            run_check(  # no pytest dep
                check,
                session,
                allow_vscode_coverage_gutters=False,
                pytest_single_threaded=True,
            )


def describe_migrate_coverage_threshold():
    @pytest.mark.parametrize(
        "table",
        [
            "tool.poe.tasks",
            "tool.poe.groups.test.tasks",
            "tool.pixi.tasks",
            "tool.pixi.feature.test.tasks",
            "tool.pixi.target.linux-64.tasks",
        ],
    )
    @pytest.mark.parametrize("option", ["--cov-fail-under=95", "--cov-fail-under 95"])
    @pytest.mark.parametrize("as_table", [False, True], ids=["string", "cmd"])
    def migrates_task_forms(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, table, option, as_table
    ):
        monkeypatch.chdir(tmp_path)
        task = f'"pytest {option} --cov=src"'
        if as_table:
            task = "{cmd = " + task + "}"
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[dependency-groups]\ntest = ["pytest-cov"]\n'
            "[tool.coverage.report]\nfail_under = 80\n"
            f"[{table}]\n"
            f"cov = {task}\n"
            'test = "pytest"\n'
        )
        with Session.load() as session:
            _migrate_coverage_threshold(session)
        result = tomli.loads(path.read_text())
        assert result["tool"]["coverage"]["report"]["fail_under"] == 95
        assert "--cov-fail-under" not in path.read_text()
        assert "--cov=src" in path.read_text()
        original = path.read_text()
        with Session.load() as session:
            _migrate_coverage_threshold(session)
            assert session.collect_changes() == []
        assert path.read_text() == original

    @pytest.mark.parametrize("threshold", [0, 92.5, 100])
    def migrates_standalone_pixi(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, threshold
    ):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "pyproject.toml"
        path.write_text('[dependency-groups]\ntest = ["pytest-cov"]\n')
        pixi = tmp_path / "pixi.toml"
        pixi.write_text(
            "[feature.test.tasks]\n"
            f'cov = "pytest --cov-fail-under={threshold} --cov=src"\n'
        )
        with Session.load() as session:
            _migrate_coverage_threshold(session)
        assert (
            tomli.loads(path.read_text())["tool"]["coverage"]["report"]["fail_under"]
            == threshold
        )
        assert "--cov-fail-under" not in pixi.read_text()

    def leaves_unchanged_pixi_out_of_changelog(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            dedent("""\
                [tool.poe.tasks]
                cov = "pytest --cov-fail-under=95"
            """)
        )
        pixi = tmp_path / "pixi.toml"
        pixi.write_text('[tasks]\ntest = "pytest"\n')
        with Session.load() as session:
            _migrate_coverage_threshold(session)
            assert session.pixi.changelog == []
            assert session.pyproject is not None
            assert session.pyproject.changelog != []

    def preserves_multiline_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "pyproject.toml"
        path.write_text(
            dedent(r'''            [dependency-groups]
            test = ["pytest-cov"]
            [tool.poe.groups.test.tasks.cov]
            cmd = """
            pytest \
                --cov=src \
                --cov-fail-under=95 \
                --cov-report=xml
            """
        ''').lstrip()
        )
        with Session.load() as session:
            _migrate_coverage_threshold(session)
        assert (
            dedent(r'''
            cmd = """
            pytest \
                --cov=src \
                --cov-report=xml
            """
        ''')
            in path.read_text()
        )

    @pytest.mark.parametrize(
        "command",
        [
            "pytest --cov=src",
            "pytest --cov-fail-under=${floor}",
            "pytest --cov-fail-under=95suffix",
        ],
    )
    def leaves_unmatched_tasks_unchanged(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command
    ):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "pyproject.toml"
        contents = (
            '[dependency-groups]\ntest = ["pytest-cov"]\n'
            "[tool.poe.tasks]\n"
            f'cov = "{command}"\n'
        )
        path.write_text(contents)
        with Session.load() as session:
            _migrate_coverage_threshold(session)
            assert session.collect_changes() == []
        assert path.read_text() == contents

    def rejects_conflicting_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "pyproject.toml"
        contents = dedent("""\
            [dependency-groups]
            test = ["pytest-cov"]
            [tool.poe.tasks]
            cov = "pytest --cov-fail-under=90"
            [tool.poe.groups.test.tasks]
            cov = "pytest --cov-fail-under=95"
        """)
        path.write_text(contents)
        with pytest.raises(PolicyError, match="conflicting"), Session.load() as session:
            _migrate_coverage_threshold(session)
        assert path.read_text() == contents


def describe_migrate_codecov_threshold():
    @pytest.mark.parametrize(
        ("target", "task_floor", "existing_floor", "expected"),
        [
            ("95%", 90, 80, 95),
            (95, 90, None, 95),
            (92.5, None, None, 92.5),
            ("92.5%", 90, None, 92.5),
            (0, 90, 80, 0),
            ("auto", 90, 80, 90),
            ("auto", None, 80, 80),
            ("auto", None, None, None),
            (None, 90, None, 90),
            (None, None, None, None),
        ],
    )
    def imports_codecov_first_and_removes_old_settings(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        target,
        task_floor,
        existing_floor,
        expected,
    ):
        monkeypatch.chdir(tmp_path)
        path = tmp_path / "pyproject.toml"
        contents = '[dependency-groups]\ntest = ["pytest-cov"]\n'
        if existing_floor is not None:
            contents += f"[tool.coverage.report]\nfail_under = {existing_floor}\n"
        if task_floor is not None:
            contents += (
                "[tool.poe.tasks]\n"
                f'cov = "pytest --cov=src --cov-fail-under={task_floor}"\n'
            )
        path.write_text(contents)
        codecov = tmp_path / "codecov.yml"
        codecov.write_text(
            dedent("""\
            # Keep other repository settings
            coverage:
              status:
                project:
                  default:
                    threshold: 1%
                    paths: [src/]
                patch:
                  default:
                    target: 80%
                    paths: null
            comment: false
        """)
        )
        if target is not None:
            codecov.write_text(
                codecov.read_text().replace(
                    "threshold: 1%", f"target: {target}\n        threshold: 1%"
                )
            )
        with Session.load() as session:
            _migrate_coverage_threshold(session)
        result = tomli.loads(path.read_text())
        assert (
            result
            .get("tool", {})
            .get("coverage", {})
            .get("report", {})
            .get("fail_under")
            == expected
        )
        assert "--cov-fail-under" not in path.read_text()
        config = yaml.safe_load(codecov.read_text())
        assert config["coverage"]["status"]["project"]["default"] == {"paths": ["src/"]}
        assert config["coverage"]["status"]["patch"]["default"]["target"] == "80%"
        assert "paths: null" in codecov.read_text()
        assert "# Keep other repository settings" in codecov.read_text()
        assert config["comment"] is False
        original = (path.read_text(), codecov.read_text())
        with Session.load() as session:
            _migrate_coverage_threshold(session)
            assert session.collect_changes() == []
        assert (path.read_text(), codecov.read_text()) == original

    @pytest.mark.parametrize("project", ["false", "{default: false}", "true"])
    def leaves_checks_without_settings_unchanged(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, project
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.coverage.report]\nfail_under = 85\n"
        )
        path = tmp_path / "codecov.yml"
        contents = f"coverage:\n  status:\n    project: {project}\n"
        path.write_text(contents)
        with Session.load() as session:
            _migrate_coverage_threshold(session)
            assert session.collect_changes() == []
        assert path.read_text() == contents
