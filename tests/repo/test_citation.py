import io
import json
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PolicyError
from compwa_policy.repo import citation
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session

_ZENODO = {
    "title": "My Software",
    "description": "<p>Some <b>HTML</b> description</p>",
    "creators": [
        {"name": "Doe, John", "affiliation": "University", "orcid": "0000-0001"},
        {"name": "Jane Smith"},
    ],
    "keywords": ["physics"],
    "license": "MIT",
}

_VALID_CITATION = """
cff-version: 1.2.0
message: If you use this software, please cite it as below.
title: My Software
abstract: Some description
authors:
  - family-names: Doe
    given-names: John
keywords:
  - physics
license: MIT
repository-code: https://github.com/ComPWA/policy
"""


def describe_convert_zenodo():
    def converts_full_metadata():
        result = citation._convert_zenodo(_ZENODO)
        assert result["title"] == "My Software"
        assert "HTML" in result["abstract"]
        assert result["authors"][0] == {
            "family-names": "Doe",
            "given-names": "John",
            "affiliation": "University",
            "orcid": "https://orcid.org/0000-0001",
        }
        assert result["authors"][1] == {"family-names": "Smith", "given-names": "Jane"}
        assert result["keywords"] == ["physics"]
        assert result["license"] == "MIT"

    def omits_absent_fields():
        result = citation._convert_zenodo({"title": "Bare"})
        assert result["title"] == "Bare"
        assert "abstract" not in result
        assert "authors" not in result  # no creators
        assert "keywords" not in result
        assert "license" not in result


def describe_convert_zenodo_json():
    def writes_citation_cff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".zenodo.json").write_text(json.dumps(_ZENODO))
        changes = citation.convert_zenodo_json()
        assert any("Converted" in m for m in changes)
        assert not (tmp_path / ".zenodo.json").exists()
        assert (tmp_path / "CITATION.cff").exists()


def describe_remove_zenodo_json():
    def removes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".zenodo.json").write_text("{}")
        changes = citation.remove_zenodo_json()
        assert any("Removed" in m for m in changes)
        assert not (tmp_path / ".zenodo.json").exists()


def describe_check_citation_keys():
    def reports_missing_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text("cff-version: 1.2.0\n")
        with pytest.raises(PolicyError, match=r"missing the following keys"):
            citation.check_citation_keys()

    def reports_empty_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text("")
        with pytest.raises(PolicyError, match=r"is empty"):
            citation.check_citation_keys()

    def accepts_complete_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        citation.check_citation_keys()  # all expected keys present -> no error


def describe_add_json_schema_precommit():
    def adds_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit:
            citation.add_json_schema_precommit(precommit)
        assert any("Updated pre-commit hook" in m for m in precommit.changelog)
        assert "check-jsonschema" in precommit.dumps()

    def is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # cspell:ignore schemafile
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        existing = dedent("""
            repos:
              - repo: https://github.com/python-jsonschema/check-jsonschema
                rev: 0.28.0
                hooks:
                  - id: check-jsonschema
                    name: Check CITATION.cff
                    args:
                      - --default-filetype
                      - yaml
                      - --schemafile
                      - https://citation-file-format.github.io/1.2.0/schema.json
                      - CITATION.cff
                    pass_filenames: false
        """).lstrip()
        with ModifiablePrecommit.load(io.StringIO(existing)) as precommit:
            citation.add_json_schema_precommit(
                precommit
            )  # already present -> no change

    def replaces_outdated_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        existing = dedent("""
            repos:
              - repo: https://github.com/python-jsonschema/check-jsonschema
                rev: 0.28.0
                hooks:
                  - id: check-jsonschema
                    name: Check CITATION.cff
                    args:
                      - --schemafile
                      - https://example.test/outdated-schema.json
                      - CITATION.cff
        """).lstrip()
        with ModifiablePrecommit.load(io.StringIO(existing)) as precommit:
            citation.add_json_schema_precommit(precommit)
        assert any("Updated pre-commit hook" in m for m in precommit.changelog)
        result = precommit.dumps()
        assert "outdated-schema" not in result  # stale args replaced
        assert "citation-file-format.github.io/1.2.0/schema.json" in result

    def is_noop_without_citation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        with ModifiablePrecommit.load(io.StringIO("repos: []\n")) as precommit:
            citation.add_json_schema_precommit(precommit)  # no CITATION.cff -> no-op

    def appends_to_existing_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        existing = dedent("""
            repos:
              - repo: https://github.com/python-jsonschema/check-jsonschema
                rev: 0.28.0
                hooks:
                  - id: check-jsonschema
                    name: Check GitHub Workflows
                    files: ^\\.github/workflows/
        """).lstrip()
        with ModifiablePrecommit.load(io.StringIO(existing)) as precommit:
            citation.add_json_schema_precommit(precommit)
        assert any("Updated pre-commit hook" in m for m in precommit.changelog)
        result = precommit.dumps()
        assert "Check GitHub Workflows" in result  # original hook kept
        assert "Check CITATION.cff" in result  # new hook appended


def describe_main():
    def processes_citation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        precommit = ModifiablePrecommit.load(io.StringIO("repos: []\n"))
        with Session.load(precommit) as session:
            citation.main(session)
        assert "check-jsonschema" in precommit.dumps()

    def converts_zenodo_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Regression test for https://github.com/ComPWA/policy/issues/616."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".zenodo.json").write_text(json.dumps(_ZENODO))
        precommit = ModifiablePrecommit.load(io.StringIO("repos: []\n"))
        with Session.load(precommit) as session:
            citation.main(session)
        assert not (tmp_path / ".zenodo.json").exists()
        assert (tmp_path / "CITATION.cff").exists()
        assert "check-jsonschema" in precommit.dumps()

    def reports_vscode_settings_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "extensions.json").write_text(
            json.dumps({"recommendations": ["redhat.vscode-yaml"]})
        )
        precommit_config = dedent("""
            repos:
              - repo: https://github.com/python-jsonschema/check-jsonschema
                rev: 0.28.0
                hooks:
                  - id: check-jsonschema
                    name: Check CITATION.cff
                    args:
                      - --default-filetype
                      - yaml
                      - --schemafile
                      - https://citation-file-format.github.io/1.2.0/schema.json
                      - CITATION.cff
                    pass_filenames: false
        """).lstrip()
        precommit = ModifiablePrecommit.load(io.StringIO(precommit_config))
        with Session.load(precommit) as session:
            citation.main(session)
            changes = session.collect_changes()
        assert changes == ["Updated VS Code settings"]
        assert (vscode_dir / "settings.json").exists()

    def removes_zenodo_when_citation_present(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".zenodo.json").write_text(json.dumps(_ZENODO))
        (tmp_path / "CITATION.cff").write_text(_VALID_CITATION)
        precommit = ModifiablePrecommit.load(io.StringIO("repos: []\n"))
        with Session.load(precommit) as session:
            citation.main(session)
        assert not (tmp_path / ".zenodo.json").exists()
        assert (tmp_path / "CITATION.cff").exists()
