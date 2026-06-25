"""Tests for the Typer-based ``policy`` command-line interface."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
import typer
import yaml

from compwa_policy.cli._options import TypeChecker, build_arguments
from compwa_policy.cli._settings import _read_policy_config, load_settings
from compwa_policy.cli.migrate import _build_policy, _render, migrate

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)  # noqa: RUF076
def _isolate_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test in an empty directory, away from the repo's own pyproject.toml."""
    monkeypatch.chdir(tmp_path)


def _write_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, table: str) -> None:
    (tmp_path / "pyproject.toml").write_text(dedent(table))
    monkeypatch.chdir(tmp_path)


def _write_precommit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: str
) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    config_file = tmp_path / ".pre-commit-config.yaml"
    config_file.write_text(dedent(config).lstrip())
    return config_file


_CONFIG_WITH_NOTEBOOK_HOOK = """\
repos:
  - repo: https://github.com/ComPWA/policy
    rev: 0.1.0
    hooks:
      - id: check-dev-files
      - id: set-nb-cells
        args: [--add-install-cell]
"""


def describe_build_arguments():
    def applies_defaults() -> None:
        args = build_arguments()
        assert args.dev_python_version == "3.13"
        assert args.package_manager == "uv"
        assert args.repo_organization == "ComPWA"
        assert args.type_checker == set()
        assert args.excluded_python_versions == set()
        assert args.keep_workflow == set()
        assert args.branch_coverage is True
        assert args.python is None

    def post_processes_options() -> None:
        # cspell:ignore myproj
        args = build_arguments(
            type_checker=[TypeChecker.mypy, TypeChecker.ty],
            excluded_python_versions="3.6, 3.7",
            macos_python_version="disable",
            repo_name="myproj",
        )
        assert args.type_checker == {"mypy", "ty"}
        assert args.excluded_python_versions == {"3.6", "3.7"}
        assert args.macos_python_version is None
        assert args.repo_name == "myproj"
        assert args.repo_title == "myproj"  # falls back to repo_name


def describe_pyproject_config():
    def treats_absent_table_as_empty(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(tmp_path, monkeypatch, '[project]\nname = "x"\n')
        assert _read_policy_config() == {}

    def flattens_nested_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            dev-python-version = "3.12"
            package-manager = "pixi"

            [tool.compwa.policy.python]
            branch-coverage = false
            imports-on-top = true
            type-checker = ["mypy", "pyright"]

            [tool.compwa.policy.nb]
            no-binder = true

            [tool.compwa.policy.setup]
            keep-contributing-md = true

            [tool.compwa.policy.setup.env]
            PYTHONHASHSEED = "0"
            MPLBACKEND = "agg"
            """,
        )
        assert _read_policy_config() == {
            "dev_python_version": "3.12",
            "package_manager": "pixi",
            "branch_coverage": False,
            "imports_on_top": True,
            "type_checker": ["mypy", "pyright"],
            "no_binder": True,
            "keep_contributing_md": True,
            "environment_variables": {
                "PYTHONHASHSEED": "0",
                "MPLBACKEND": "agg",
            },
        }

    def overrides_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            dev-python-version = "3.12"

            [tool.compwa.policy.python]
            branch-coverage = false
            type-checker = ["mypy", "pyright"]

            [tool.compwa.policy.setup.env]
            PYTHONHASHSEED = "0"
            """,
        )
        args = build_arguments()
        assert args.dev_python_version == "3.12"
        assert args.branch_coverage is False
        assert args.type_checker == {"mypy", "pyright"}
        assert args.environment_variables == "PYTHONHASHSEED=0"

    def yields_to_cli_options(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            dev-python-version = "3.12"
            """,
        )
        assert load_settings(dev_python_version="3.11").dev_python_version == "3.11"
        assert load_settings(dev_python_version=None).dev_python_version == "3.12"

    def cli_branch_coverage_overrides_pyproject(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy.python]
            branch-coverage = false
            """,
        )
        assert load_settings(branch_coverage=True).branch_coverage is True

    def rejects_unknown_option(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_policy(
            tmp_path,
            monkeypatch,
            """
            [tool.compwa.policy]
            does-not-exist = true
            """,
        )
        with pytest.raises(ValueError, match="does_not_exist"):
            load_settings()

    def ignores_environment_variables(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_policy(tmp_path, monkeypatch, '[project]\nname = "x"\n')
        monkeypatch.setenv("NO_PYPI", "true")
        monkeypatch.setenv("PACKAGE_MANAGER", "pixi")
        settings = load_settings()
        assert settings.no_pypi is False
        assert settings.package_manager == "uv"


def describe_build_policy():
    def groups_into_sub_tables() -> None:
        policy = _build_policy([
            "--allow-labels",
            "--no-branch-coverage",
            "--no-pypi",
            "--pytest-single-threaded",
            "--repo-name=policy",
            "--repo-title=ComPWA repository policy",
            "--type-checker=ty",
        ])
        assert policy == {
            "github": {"allow-labels": True, "no-pypi": True},
            "python": {
                "branch-coverage": False,
                "type-checker": ["ty"],
            },
            "pytest-single-threaded": True,
            "repo-name": "policy",
            "repo-title": "ComPWA repository policy",
        }

    def collects_repeated_list_option() -> None:
        policy = _build_policy(["--type-checker=mypy", "--type-checker=pyright"])
        assert policy == {"python": {"type-checker": ["mypy", "pyright"]}}

    def maps_environment_variables_to_setup_env() -> None:
        policy = _build_policy([
            "--environment-variables=PYTHONHASHSEED=0,MPLBACKEND=agg"
        ])
        assert policy == {
            "setup": {"env": {"PYTHONHASHSEED": "0", "MPLBACKEND": "agg"}}
        }

    def handles_no_python_flag() -> None:
        assert _build_policy(["--no-python"]) == {"python": False}
        assert _build_policy(["--python"]) == {"python": True}

    def round_trips_through_settings(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        args = [
            "--allow-labels",
            "--no-pypi",
            "--repo-name=policy",
            "--type-checker=ty",
        ]
        policy = _build_policy(args)
        _write_policy(tmp_path, monkeypatch, _render(policy))
        settings = load_settings()
        assert settings.repo_name == "policy"
        assert settings.allow_labels is True
        assert settings.no_pypi is True
        assert settings.type_checker == ["ty"]


def describe_migrate():
    def describe_notebook_hooks():
        def relocates_to_nbhooks(tmp_path: Path) -> None:
            (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
            config = tmp_path / ".pre-commit-config.yaml"
            config.write_text(_CONFIG_WITH_NOTEBOOK_HOOK)

            migrate(config_file=config, dry_run=False)

            repos = {
                repo["repo"]: repo
                for repo in yaml.safe_load(config.read_text())["repos"]
            }
            policy_hooks = {
                h["id"] for h in repos["https://github.com/ComPWA/policy"]["hooks"]
            }
            assert policy_hooks == {"check-dev-files"}
            nbhooks = repos["https://github.com/ComPWA/nbhooks"]
            assert nbhooks["rev"] == "PLEASE-UPDATE"
            assert {h["id"] for h in nbhooks["hooks"]} == {"set-nb-cells"}
            set_nb_cells = next(
                h for h in nbhooks["hooks"] if h["id"] == "set-nb-cells"
            )
            assert set_nb_cells["args"] == ["--add-install-cell"], (
                "args must be preserved"
            )

        def dry_run_does_not_modify(tmp_path: Path) -> None:
            (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
            config = tmp_path / ".pre-commit-config.yaml"
            config.write_text(_CONFIG_WITH_NOTEBOOK_HOOK)
            with pytest.raises(typer.Exit):
                migrate(config_file=config, dry_run=True)
            assert config.read_text() == _CONFIG_WITH_NOTEBOOK_HOOK

    def exits_on_missing_config_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        with pytest.raises(typer.Exit) as exc:
            migrate(config_file=tmp_path / "does-not-exist.yaml")
        assert exc.value.exit_code == 1

    def exits_on_missing_pyproject(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config = tmp_path / ".pre-commit-config.yaml"
        config.write_text("repos: []\n")
        with pytest.raises(typer.Exit) as exc:
            migrate(config_file=config)
        assert exc.value.exit_code == 1

    def exits_when_no_hook_found(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = _write_precommit(
            tmp_path,
            monkeypatch,
            """
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
            """,
        )
        with pytest.raises(typer.Exit) as exc:
            migrate(config_file=config)
        assert exc.value.exit_code == 0

    def exits_when_nothing_to_migrate(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = _write_precommit(
            tmp_path,
            monkeypatch,
            """
            repos:
              - repo: local
                hooks:
                  - id: check-dev-files
            """,
        )
        with pytest.raises(typer.Exit) as exc:
            migrate(config_file=config)
        assert exc.value.exit_code == 0

    def exits_on_unknown_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = _write_precommit(
            tmp_path,
            monkeypatch,
            """
            repos:
              - repo: https://github.com/ComPWA/policy
                rev: 0.1.0
                hooks:
                  - id: check-dev-files
                    args: [--does-not-exist]
            """,
        )
        with pytest.raises(typer.Exit) as exc:
            migrate(config_file=config)
        assert exc.value.exit_code == 1

    def migrates_args_into_pyproject(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = _write_precommit(
            tmp_path,
            monkeypatch,
            """
            repos:
              - repo: https://github.com/ComPWA/policy
                rev: 0.1.0
                hooks:
                  - id: check-dev-files
                    args: [--no-pypi, --repo-name=demo, --type-checker=ty]
            """,
        )
        migrate(config_file=config, dry_run=False)

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert "no-pypi = true" in pyproject
        assert 'repo-name = "demo"' in pyproject
        hooks = yaml.safe_load(config.read_text())["repos"][0]["hooks"]
        assert "args" not in hooks[0], "args must be stripped after migration"

    def migrates_environment_variables_into_nested_table(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config = _write_precommit(
            tmp_path,
            monkeypatch,
            """
            repos:
              - repo: https://github.com/ComPWA/policy
                rev: 0.1.0
                hooks:
                  - id: check-dev-files
                    args: ["--environment-variables=A=1,B=2"]
            """,
        )
        migrate(config_file=config, dry_run=False)

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.compwa.policy.setup.env]" in pyproject
        assert 'A = "1"' in pyproject
        assert 'B = "2"' in pyproject
