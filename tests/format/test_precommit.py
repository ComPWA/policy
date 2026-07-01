from __future__ import annotations

import io
from textwrap import dedent
from typing import TYPE_CHECKING

import yaml

from compwa_policy.format import precommit
from compwa_policy.utilities.precommit import ModifiablePrecommit, Precommit

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _load(content: str) -> ModifiablePrecommit:
    return ModifiablePrecommit.load(io.StringIO(dedent(content).lstrip()))


_CONFIG_WITH_NOTEBOOK_HOOK = """\
repos:
  - repo: https://github.com/ComPWA/policy
    rev: 0.1.0
    hooks:
      - id: check-dev-files
      - id: set-nb-cells
        args: [--add-install-cell]
"""

_POLICY_URL = "https://github.com/ComPWA/policy"
_NBHOOKS_URL = "https://github.com/ComPWA/nbhooks"


def _run(config: str, *, has_notebooks: bool) -> tuple[bool, str]:
    """Run the migration and report whether it changed anything and the result.

    Tags cannot be fetched (the ``_offline_git_ls_remote`` fixture), so the new
    ComPWA/nbhooks repo entry is pinned to the fallback revision ``PLEASE-UPDATE``.
    """
    stream = io.StringIO(config)
    with ModifiablePrecommit.load(stream) as pc:
        precommit._update_notebook_hooks(pc, has_notebooks=has_notebooks)
    changed = bool(pc.changelog)
    return changed, stream.getvalue()


def describe_update_notebook_hooks():
    def migrates_notebook_hooks_to_nbhooks():
        changed, result = _run(_CONFIG_WITH_NOTEBOOK_HOOK, has_notebooks=True)
        assert changed
        repos = {repo["repo"]: repo for repo in yaml.safe_load(result)["repos"]}

        policy_hook_ids = {hook["id"] for hook in repos[_POLICY_URL]["hooks"]}
        assert policy_hook_ids == {"check-dev-files"}

        nbhooks = repos[_NBHOOKS_URL]
        assert nbhooks["rev"] == "PLEASE-UPDATE"
        nbhooks_ids = {hook["id"] for hook in nbhooks["hooks"]}
        assert nbhooks_ids == {
            "remove-empty-tags",
            "set-nb-cells",
            "set-nb-display-name",
            "strip-nb-whitespace",
        }
        set_nb_cells = next(h for h in nbhooks["hooks"] if h["id"] == "set-nb-cells")
        assert set_nb_cells["args"] == ["--add-install-cell"], "args must be preserved"

    def is_idempotent():
        _, migrated = _run(_CONFIG_WITH_NOTEBOOK_HOOK, has_notebooks=True)
        changed, _ = _run(migrated, has_notebooks=True)
        assert not changed

    def only_migrates_existing_hooks_without_notebooks():
        changed, result = _run(_CONFIG_WITH_NOTEBOOK_HOOK, has_notebooks=False)
        assert changed
        repos = {repo["repo"]: repo for repo in yaml.safe_load(result)["repos"]}
        nbhooks_ids = {hook["id"] for hook in repos[_NBHOOKS_URL]["hooks"]}
        assert nbhooks_ids == {"set-nb-cells"}, "no defaults added without notebooks"


def describe_sort_hooks():
    def sorts_meta_before_repos():
        with _load("""
                repos:
                  - repo: https://github.com/psf/black
                    hooks:
                      - id: black
                  - repo: meta
                    hooks:
                      - id: check-hooks-apply
            """) as pc:
            precommit._sort_hooks(pc)
        assert any("Sorted all pre-commit hooks" in m for m in pc.changelog)
        result = pc.dumps()
        assert result.index("meta") < result.index("psf/black")

    def orders_all_categories():
        with _load("""
                repos:
                  - repo: https://github.com/some/other
                    hooks:
                      - id: some-hook
                  - repo: https://github.com/x/prettier
                    hooks:
                      - id: prettier
                  - repo: https://github.com/multi/repo
                    hooks:
                      - id: hook-a
                      - id: hook-b
                  - repo: https://github.com/nbqa-dev/nbQA
                    hooks:
                      - id: nbqa-isort
                  - repo: https://github.com/kynan/nbstripout
                    hooks:
                      - id: nbstripout
                  - repo: https://github.com/ComPWA/policy
                    hooks:
                      - id: check-dev-files
                  - repo: meta
                    hooks:
                      - id: check-hooks-apply
            """) as pc:
            precommit._sort_hooks(pc)
        result = pc.dumps()
        expected_order = [
            "meta",
            "ComPWA/policy",
            "nbstripout",
            "nbqa-isort",
            "multi/repo",
            "x/prettier",
            "some/other",
        ]
        positions = [result.index(token) for token in expected_order]
        assert positions == sorted(positions)


def describe_update_precommit_ci():
    def is_noop_without_ci_section():
        with _load("""
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply
        """) as pc:
            precommit._update_precommit_ci_autofix_commit_msg(pc)
            precommit._update_precommit_ci_autoupdate_commit_msg(pc)
            precommit._update_precommit_ci_skip(pc)  # no ci section -> nothing to do

    def sets_autofix_commit_msg():
        with _load("""
                ci:
                  autofix_prs: true
                repos: []
            """) as pc:
            precommit._update_precommit_ci_autofix_commit_msg(pc)
        assert any("autofix_commit_msg" in m for m in pc.changelog)
        assert "MAINT: implement pre-commit autofixes" in pc.dumps()

    def skip_collects_local_and_non_functional_hooks():
        with _load("""
                ci:
                  autofix_prs: true
                repos:
                  - repo: local
                    hooks:
                      - id: my-local-hook
                  - repo: https://github.com/astral-sh/ty-pre-commit
                    rev: v0.0.1
                    hooks:
                      - id: ty
            """) as pc:
            precommit._update_precommit_ci_skip(pc)
        assert any("Updated ci.skip" in m for m in pc.changelog)
        result = pc.dumps()
        assert "my-local-hook" in result
        assert "ty" in result

    def skip_removes_redundant_section():
        with _load("""
                ci:
                  skip:
                    - some-hook
                repos:
                  - repo: meta
                    hooks:
                      - id: check-hooks-apply
            """) as pc:
            precommit._update_precommit_ci_skip(pc)
        assert any("Removed redundant ci.skip" in m for m in pc.changelog)
        assert "skip" not in pc.dumps()


def describe_update_repo_urls():
    def migrates_repo_maintenance_url():
        with _load("""
                repos:
                  - repo: https://github.com/ComPWA/repo-maintenance
                    rev: "1.0"
                    hooks:
                      - id: check-dev-files
            """) as pc:
            precommit._update_repo_urls(pc)
        assert any("Updated repo URLs" in m for m in pc.changelog)
        assert _POLICY_URL in pc.dumps()


def describe_get_local_and_non_functional_hooks():
    def separates_local_from_non_functional():
        config = Precommit.load(
            io.StringIO(
                dedent("""
                repos:
                  - repo: local
                    hooks:
                      - id: my-local-hook
                  - repo: https://github.com/astral-sh/ty-pre-commit
                    rev: v0.0.1
                    hooks:
                      - id: ty
                """).lstrip()
            )
        ).document
        assert precommit.get_local_hooks(config) == ["my-local-hook"]
        assert precommit.get_non_functional_hooks(config) == ["ty"]


def describe_update_conda_environment():
    def sets_legacy_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yml").write_text("dependencies:\n  - python\n")
        with ModifiablePrecommit.load(
            io.StringIO(
                dedent("""
                repos:
                  - repo: https://github.com/ComPWA/prettier-pre-commit
                    rev: v4.0.0-alpha.8
                    hooks:
                      - id: prettier
                """).lstrip()
            )
        ) as pc:
            precommit._update_conda_environment(pc)
        assert any("Set PRETTIER_LEGACY_CLI" in m for m in pc.changelog)
        assert "PRETTIER_LEGACY_CLI" in (tmp_path / "environment.yml").read_text()

    def removes_legacy_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yml").write_text(
            "variables:\n  PRETTIER_LEGACY_CLI: 1\n"
        )
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as pc:
            precommit._update_conda_environment(pc)
        assert any("Removed PRETTIER_LEGACY_CLI" in m for m in pc.changelog)
        assert "PRETTIER_LEGACY_CLI" not in (tmp_path / "environment.yml").read_text()


def describe_main():
    def reports_standalone_pyproject_changes(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("""
            [project]
            name = "x"

            [dependency-groups]
            dev = ["pre-commit", "pre-commit-uv"]
        """)
        with _load("repos: []") as pc:
            changes = precommit.main(pc, has_notebooks=False)
        assert any("Removed pre-commit from dependencies" in m for m in changes)
        assert any("Removed pre-commit-uv from dependencies" in m for m in changes)

    def sorts_and_updates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[dependency-groups]\ndev = []\n")
        with _load("""
                ci:
                  autofix_prs: true
                repos:
                  - repo: https://github.com/psf/black
                    hooks:
                      - id: black
                  - repo: meta
                    hooks:
                      - id: check-hooks-apply
            """) as pc:
            precommit.main(pc, has_notebooks=False)
        result = pc.dumps()
        assert result.index("meta") < result.index("psf/black")  # hooks sorted
