import io
import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
import tomlkit

from compwa_policy.format.toml import (
    _add_tombi_hook_and_config,
    _remove_taplo_hook_and_config,
    _remove_tomlsort_hook_and_config,
    _rename_precommit_url,
    _rename_taplo_config,
    _update_precommit_repo,
    _update_taplo_config,
    _update_tombi_vscode_extensions,
    _update_tomlsort_config,
    _update_tomlsort_hook,
    _update_vscode_extensions,
    check,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session

_META_ONLY = dedent("""
    repos:
      - repo: meta
        hooks:
          - id: check-hooks-apply
""").lstrip()

_WITH_MIRRORS_TAPLO = dedent("""
    repos:
      - repo: https://github.com/ComPWA/mirrors-taplo
        rev: v0.8.1
        hooks:
          - id: taplo
""").lstrip()


def describe_rename_precommit_url():
    def migrates_mirror():
        with ModifiablePrecommit.load(io.StringIO(_WITH_MIRRORS_TAPLO)) as precommit:
            _rename_precommit_url(precommit)
        result = precommit.dumps()
        assert any("mirrors-taplo" in m for m in precommit.changelog)
        assert "mirrors-taplo" not in result
        assert "https://github.com/ComPWA/taplo-pre-commit" in result
        assert "rev: v0.8.1" in result  # preserves the pinned revision

    def adds_hook_without_mirror():
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _rename_precommit_url(precommit)
        assert "https://github.com/ComPWA/taplo-pre-commit" in precommit.dumps()


def describe_update_precommit_repo():
    def adds_taplo():
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _update_precommit_repo(precommit)
        result = precommit.dumps()
        assert "https://github.com/ComPWA/taplo-pre-commit" in result
        assert "id: taplo-format" in result

    def migrates_mirror():
        with ModifiablePrecommit.load(io.StringIO(_WITH_MIRRORS_TAPLO)) as precommit:
            _update_precommit_repo(precommit)
        result = precommit.dumps()
        assert "mirrors-taplo" not in result
        assert "https://github.com/ComPWA/taplo-pre-commit" in result


def describe_update_tomlsort_hook():
    def adds_hook_without_excludes(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _update_tomlsort_hook(precommit)
        result = precommit.dumps()
        assert "https://github.com/pappasam/toml-sort" in result
        assert "exclude" not in result

    def adds_excludes_when_present(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        (tmp_path / "labels.toml").touch()
        monkeypatch.chdir(tmp_path)
        with ModifiablePrecommit.load(io.StringIO(_META_ONLY)) as precommit:
            _update_tomlsort_hook(precommit)
        assert "exclude" in precommit.dumps()


def describe_rename_taplo_config():
    def renames_to_dotfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "taplo.toml").write_text("include = []\n")
        changes = _rename_taplo_config()
        assert any("Renamed taplo.toml" in m for m in changes)
        assert not (tmp_path / "taplo.toml").exists()
        assert (tmp_path / ".taplo.toml").exists()


def describe_update_tomlsort_config():
    def configures_sort_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        with Session() as session:
            _update_tomlsort_config(session)
            changes = session.collect_changes()
        assert any("toml-sort" in m for m in changes)
        result = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.tomlsort]" in result
        assert 'sort_first = ["project"]' in result

    def is_idempotent_without_known_tables(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[tool.other]\nkey = 1\n")
        with Session() as session:
            _update_tomlsort_config(session)
        assert "sort_first" not in (tmp_path / "pyproject.toml").read_text()
        with Session() as session:
            _update_tomlsort_config(session)
            assert session.collect_changes() == []


def describe_update_taplo_config():
    def creates_file(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            _update_taplo_config(session)
            changes = session.collect_changes()
        assert any(".taplo.toml" in m for m in changes)
        assert (tmp_path / ".taplo.toml").exists()

    def creates_normalized_file(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            _update_taplo_config(session)
            assert session.collect_changes()
        before = (tmp_path / ".taplo.toml").read_text()
        with Session() as session:
            _update_taplo_config(session)
            assert session.collect_changes() == []
        assert (tmp_path / ".taplo.toml").read_text() == before


def describe_update_vscode_extensions():
    def recommends_even_better_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # cspell:ignore tamasfe
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            _update_vscode_extensions(session)
        extensions = (tmp_path / ".vscode" / "extensions.json").read_text()
        assert "tamasfe.even-better-toml" in extensions
        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
        assert settings["[toml]"]["editor.defaultFormatter"] == (
            "tamasfe.even-better-toml"
        )

    def recommends_tombi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with Session() as session:
            _update_tombi_vscode_extensions(session)
        extensions = json.loads((tmp_path / ".vscode" / "extensions.json").read_text())
        assert "tombi-toml.tombi" in extensions["recommendations"]
        assert "tamasfe.even-better-toml" in extensions["unwantedRecommendations"]
        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
        assert settings["[toml]"]["editor.defaultFormatter"] == "tombi-toml.tombi"


def describe_tombi_configuration():
    @pytest.mark.parametrize("tracked", [True, False], ids=["tracked", "untracked"])
    def excludes_only_tracked_manifest_files(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
        tracked: bool,
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text('[project]\nname = "x"\n')
        precommit_path = tmp_path / ".pre-commit-config.yaml"
        precommit_path.write_text(_META_ONLY)
        (tmp_path / "Manifest.toml").touch()
        if tracked:
            git_add(tmp_path)

        with Session() as session:
            _add_tombi_hook_and_config(session, session.precommit)

        assert ('"**/Manifest.toml"' in pyproject_path.read_text()) is tracked

    def optionally_treats_lint_warnings_as_errors(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        precommit_path = tmp_path / ".pre-commit-config.yaml"
        precommit_path.write_text(_META_ONLY)

        with Session() as session:
            _add_tombi_hook_and_config(
                session,
                session.precommit,
                errors_on_warnings=True,
            )

        repo = ModifiablePrecommit.load(precommit_path).find_repo("tombi-pre-commit")
        assert repo is not None
        assert repo["hooks"][1] == {
            "id": "tombi-lint",
            "args": ["--error-on-warnings"],
        }

    def associates_the_schema_from_the_policy_revision(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        precommit_path = tmp_path / ".pre-commit-config.yaml"
        precommit_path.write_text(
            dedent("""
            repos:
              - repo: https://github.com/ComPWA/policy
                rev: v0.12.3
                hooks:
                  - id: check-dev-files
        """).lstrip()
        )

        with Session() as session:
            _add_tombi_hook_and_config(session, session.precommit)

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert 'root = "tool.compwa.policy"' in pyproject
        assert "https://raw.githubusercontent.com/ComPWA/policy/v0.12.3/" in pyproject
        assert "compwa-policy.schema.json" in pyproject

    def preserves_repository_specific_schemas(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            dedent("""
                [project]
                name = "x"

                [[tool.tombi.schemas]]
                root = "tool.pwa"
                path = "pwa.schema.json"
                include = ["pyproject.toml"]

                [[tool.tombi.schemas]]
                path = "pwa.schema.json"
                include = ["pwa.toml"]

                [[tool.tombi.schemas]]
                root = "tool.compwa.policy"
                path = "outdated-policy.schema.json"
                include = ["pyproject.toml"]
            """).lstrip()
        )
        (tmp_path / ".pre-commit-config.yaml").write_text(
            dedent("""
                repos:
                  - repo: https://github.com/ComPWA/policy
                    rev: v0.12.3
                    hooks:
                      - id: check-dev-files
            """).lstrip()
        )

        with Session() as session:
            _add_tombi_hook_and_config(session, session.precommit)

        tombi = tomlkit.loads((tmp_path / "pyproject.toml").read_text())["tool"][
            "tombi"
        ]
        assert tombi["schemas"] == [
            {
                "root": "tool.pwa",
                "path": "pwa.schema.json",
                "include": ["pyproject.toml"],
            },
            {
                "path": "pwa.schema.json",
                "include": ["pwa.toml"],
            },
            {
                "root": "tool.compwa.policy",
                "path": "https://raw.githubusercontent.com/ComPWA/policy/v0.12.3/compwa-policy.schema.json",
                "include": ["pyproject.toml"],
            },
        ]

    def follows_tombi_table_order(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        (tmp_path / "uv.lock").touch()
        (tmp_path / ".pre-commit-config.yaml").write_text(
            dedent("""
            repos:
              - repo: https://github.com/ComPWA/policy
                rev: v0.12.3
                hooks:
                  - id: check-dev-files
        """).lstrip()
        )
        git_add(tmp_path)

        with Session() as session:
            _add_tombi_hook_and_config(session, session.precommit)

        pyproject = (tmp_path / "pyproject.toml").read_text()
        files_position = pyproject.index("[tool.tombi.files]")
        format_position = pyproject.index("[tool.tombi.format.rules]")
        lint_position = pyproject.index("[tool.tombi.lint.rules]")
        schemas_position = pyproject.index("[[tool.tombi.schemas]]")
        assert files_position < format_position < lint_position < schemas_position

    def replaces_taplo_and_tomlsort(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".taplo.toml").write_text("[formatting]\ncolumn_width = 88\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\n\n[tool.tomlsort]\nin_place = true\n'
        )
        precommit_path = tmp_path / ".pre-commit-config.yaml"
        precommit_path.write_text(
            dedent("""
                repos:
                  - repo: https://github.com/ComPWA/taplo-pre-commit
                    rev: v0.9.3
                    hooks:
                      - id: taplo-format
                  - repo: https://github.com/pappasam/toml-sort
                    rev: v0.24.4
                    hooks:
                      - id: toml-sort
                        args: [--in-place]
            """).lstrip()
        )
        with Session() as session:
            precommit = session.precommit
            _remove_taplo_hook_and_config(session, precommit)
            _remove_tomlsort_hook_and_config(session, precommit)
            _add_tombi_hook_and_config(session, precommit)
        result = precommit_path.read_text()
        assert "taplo" not in result
        assert "toml-sort" not in result
        assert "https://github.com/tombi-toml/tombi-pre-commit" in result
        assert "id: tombi-format" in result
        assert "id: tombi-lint" in result
        assert not (tmp_path / ".taplo.toml").exists()
        assert "[tool.tomlsort]" not in (tmp_path / "pyproject.toml").read_text()
        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert "[tool.tombi.format.rules]" in pyproject
        assert "indent-width = 4" in pyproject
        assert "line-width = 88" in pyproject
        assert "[tool.tombi.lint.rules]" in pyproject
        assert 'key-empty = "off"' in pyproject
        assert "[tool.tombi.files]" not in pyproject
        assert not (tmp_path / "tombi.toml").exists()

    def is_idempotent(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        precommit_path = tmp_path / ".pre-commit-config.yaml"
        precommit_path.write_text(_META_ONLY)
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text('[project]\nname = "x"\n')
        with Session() as session:
            _add_tombi_hook_and_config(session, session.precommit)
        before = pyproject_path.read_text()
        with Session() as session:
            _add_tombi_hook_and_config(session, session.precommit)
            assert session.collect_changes() == []
        assert pyproject_path.read_text() == before


def describe_main():
    def runs_when_triggered(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        git_add(tmp_path)
        precommit = ModifiablePrecommit.load(io.StringIO(_META_ONLY))
        with Session.load(precommit) as session:
            run_check(check, session)
            changes = session.collect_changes()
        result = precommit.dumps()
        assert changes or precommit.changelog
        assert "https://github.com/tombi-toml/tombi-pre-commit" in result
        assert "id: tombi-format" in result
        assert "id: tombi-lint" in result
        assert "[tool.tombi.format.rules]" in (tmp_path / "pyproject.toml").read_text()

    def removes_formatters_without_committed_toml(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "settings.json").write_text(
            '{"[toml]": {"editor.defaultFormatter": "tombi-toml.tombi"}}'
        )
        precommit_path = tmp_path / ".pre-commit-config.yaml"
        precommit_path.write_text(
            dedent("""
                repos:
                  - repo: https://github.com/ComPWA/taplo-pre-commit
                    rev: v0.9.3
                    hooks:
                      - id: taplo-format
                  - repo: https://github.com/tombi-toml/tombi-pre-commit
                    rev: v0.6.0
                    hooks:
                      - id: tombi-format
                      - id: tombi-lint
                  - repo: https://github.com/pre-commit/pre-commit-hooks
                    rev: v6.0.0
                    hooks:
                      - id: check-json
                      - id: check-toml
            """).lstrip()
        )
        git_add(tmp_path)

        with Session() as session:
            run_check(check, session)

        result = precommit_path.read_text()
        assert "taplo" not in result
        assert "tombi" not in result
        assert "check-toml" not in result
        assert "check-json" in result
        assert not (tmp_path / ".taplo.toml").exists()
        settings = json.loads((vscode_dir / "settings.json").read_text())
        assert "[toml]" not in settings

    def configures_formatter_for_nested_toml(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        nested_toml = tmp_path / "config" / "settings.toml"
        nested_toml.parent.mkdir()
        nested_toml.write_text("enabled = true\n")
        git_add(tmp_path)
        precommit = ModifiablePrecommit.load(io.StringIO(_META_ONLY))

        with Session.load(precommit) as session:
            run_check(check, session)

        result = precommit.dumps()
        assert "id: tombi-format" in result
        assert "id: tombi-lint" in result
        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
        assert settings["[toml]"]["editor.defaultFormatter"] == "tombi-toml.tombi"

    def keeps_explicit_formatter_without_committed_toml(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".taplo.toml").write_text("include = []\n")
        precommit = ModifiablePrecommit.load(io.StringIO(_META_ONLY))
        with Session.load(precommit) as session:
            run_check(check, session, toml_formatter="tombi")

        result = precommit.dumps()
        assert "id: tombi-format" in result
        assert "id: tombi-lint" in result

    def skips_without_trigger_files(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        precommit = ModifiablePrecommit.load(io.StringIO(_META_ONLY))
        with Session.load(precommit) as session:
            run_check(check, session)  # no pyproject.toml or taplo config -> no-op
