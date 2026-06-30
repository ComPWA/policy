import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.repo.deprecated import (
    _remove_relink_references,
    remove_deprecated_tools,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit


def describe_remove_relink_references():
    def is_noop_without_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        _remove_relink_references("docs")  # nothing to remove

    def raises_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "_relink_references.py").touch()
        with pytest.raises(PrecommitError, match=r"sphinx-api-relink"):
            _remove_relink_references("docs")


def describe_remove_deprecated_tools():
    def removes_markdownlint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        config = dedent("""
            repos:
              - repo: https://github.com/igorshubovych/markdownlint-cli
                rev: v0.41.0
                hooks:
                  - id: markdownlint
        """).lstrip()
        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            changes = remove_deprecated_tools(precommit, keep_issue_templates=True)
        assert any("markdownlint" in m for m in changes) or any(
            "markdownlint" in m for m in precommit.changelog
        )

    def removes_issue_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        template_dir = tmp_path / ".github" / "ISSUE_TEMPLATE"
        template_dir.mkdir(parents=True)
        (template_dir / "bug_report.md").touch()
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit:
            changes = remove_deprecated_tools(precommit, keep_issue_templates=False)
        assert any("ISSUE_TEMPLATE" in m for m in changes)
        assert not template_dir.exists()
