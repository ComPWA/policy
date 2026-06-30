import subprocess  # noqa: S404
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.env.pixi._update import (
    _clean_up_task_env,
    _define_combined_ci_job,
    _set_dev_python_version,
    _update_dev_environment,
    _update_docnb_and_doclive,
    update_pixi_configuration,
)
from compwa_policy.utilities.pyproject import ModifiablePyproject

_ENVIRONMENT_YML = dedent("""
    dependencies:
      - python==3.12.*
      - pip
      - graphviz
    variables:
      MY_VARIABLE: "1"
""").lstrip()


def describe_update_docnb_and_doclive():
    @pytest.mark.parametrize(
        "table_key",
        [
            "tool.pixi.feature.dev.tasks",
            "tool.pixi.tasks",
        ],
    )
    def rewrites_docnb_command(table_key: str):
        content = dedent(f"""
            [{table_key}.doc]
            cmd = "command executed by doc"

            [{table_key}.docnb]
            cmd = "some outdated command"

            [{table_key}.docnb-test]
            cmd = "should not change"
        """)
        with ModifiablePyproject.load(content) as pyproject:
            _update_docnb_and_doclive(pyproject, table_key)
        assert any(
            "Updated `cmd` of Pixi tasks docnb" in m for m in pyproject.changelog
        )
        new_content = pyproject.dumps()
        expected = dedent(f"""
            [{table_key}.doc]
            cmd = "command executed by doc"

            [{table_key}.docnb]
            cmd = "pixi run doc"

            [{table_key}.docnb-test]
            cmd = "should not change"
        """)
        assert new_content.strip() == expected.strip()


def describe_update_pixi_configuration():
    def skips_non_pixi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        update_pixi_configuration(
            is_python_package=True,
            dev_python_version="3.12",
            package_manager="uv",  # not a pixi manager -> no-op
        )
        assert not (tmp_path / "pixi.toml").exists()

    def configures_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "environment.yml").write_text(_ENVIRONMENT_YML)
        (tmp_path / "pyproject.toml").write_text(
            dedent("""
            [project]
            name = "my-package"

            [tool.pixi.project]
            channels = ["conda-forge"]

            [tool.pixi.feature.dev.tasks.docnb]
            cmd = "outdated"
            """).lstrip()
        )
        update_pixi_configuration(
            is_python_package=True,
            dev_python_version="3.12",
            package_manager="pixi",
        )

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.pixi.workspace]" in pyproject  # project table renamed
        assert "graphviz" in pyproject  # conda dependency imported
        assert "MY_VARIABLE" in pyproject  # conda variable imported
        assert 'python = "3.12.*"' in pyproject  # dev Python version set
        assert "my-package" in pyproject  # installed as editable pypi-dependency
        assert 'cmd = "pixi run doc"' in pyproject  # docnb task outsourced

    def configures_pixi_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "pixi.toml").write_text(
            dedent("""
            [feature.dev.tasks.sty]
            cmd = "pre-commit run -a"

            [feature.dev.tasks.docnb]
            cmd = "build docs"
            """).lstrip()
        )
        update_pixi_configuration(
            is_python_package=True,
            dev_python_version="3.12",
            package_manager="pixi+uv",
        )

        pixi = (tmp_path / "pixi.toml").read_text()
        assert "[feature.dev.tasks.ci]" in pixi  # combined CI job defined
        assert "depends_on" in pixi


def describe_define_combined_ci_job():
    def selects_tests_and_doc():
        content = dedent("""
            [feature.dev.tasks.tests]
            cmd = "pytest"

            [feature.dev.tasks.doc]
            cmd = "build docs"
        """)
        with ModifiablePyproject.load(content) as config:
            _define_combined_ci_job(config)
        assert any("Updated combined CI job" in m for m in config.changelog)
        result = config.dumps()
        assert "tests" in result
        assert "doc" in result


def describe_clean_up_task_env():
    def removes_redundant_variables():
        content = dedent("""
            [activation.env]
            SHARED = "global"

            [feature.dev.tasks.test.env]
            SHARED = "global"
            LOCAL = "value"
        """)
        with ModifiablePyproject.load(content) as config:
            _clean_up_task_env(config)
        assert any(
            "Removed redundant environment variables" in m for m in config.changelog
        )
        result = config.dumps()
        assert "LOCAL" in result
        assert result.count("SHARED") == 1  # only the global activation entry remains


def describe_update_dev_environment():
    def lists_optional_dependency_features():
        content = dedent("""
            [project.optional-dependencies]
            dev = ["pytest"]
            doc = ["sphinx"]
        """)
        with ModifiablePyproject.load(content) as config:
            _update_dev_environment(config)
        assert any("Updated Pixi developer environment" in m for m in config.changelog)
        result = config.dumps()
        assert "features" in result
        assert "doc" in result


def describe_set_dev_python_version():
    def sets_version():
        content = dedent("""
            [dependencies]
            python = "3.10.*"
        """)
        with ModifiablePyproject.load(content) as config:
            _set_dev_python_version(config, "3.12")
        assert any("Set Python version" in m for m in config.changelog)
        assert 'python = "3.12.*"' in config.dumps()
