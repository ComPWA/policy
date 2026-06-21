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


def test_remove_relink_references_without_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    _remove_relink_references("docs")  # nothing to remove


def test_remove_relink_references_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "_relink_references.py").touch()
    with pytest.raises(PrecommitError, match=r"sphinx-api-relink"):
        _remove_relink_references("docs")


def test_remove_deprecated_tools_removes_markdownlint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    config = dedent("""
        repos:
          - repo: https://github.com/igorshubovych/markdownlint-cli
            rev: v0.41.0
            hooks:
              - id: markdownlint
    """).lstrip()
    with (
        pytest.raises(PrecommitError, match=r"markdownlint"),
        ModifiablePrecommit.load(io.StringIO(config)) as precommit,
    ):
        remove_deprecated_tools(precommit, keep_issue_templates=True)


def test_remove_deprecated_tools_removes_issue_templates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    template_dir = tmp_path / ".github" / "ISSUE_TEMPLATE"
    template_dir.mkdir(parents=True)
    (template_dir / "bug_report.md").touch()
    with (
        ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit,
        pytest.raises(PrecommitError, match=r"Removed \.github/ISSUE_TEMPLATE"),
    ):
        remove_deprecated_tools(precommit, keep_issue_templates=False)
    assert not template_dir.exists()
