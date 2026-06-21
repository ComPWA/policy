from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.ty import _update_precommit_config
from compwa_policy.utilities.precommit import ModifiablePrecommit


def _run_update(config: Path) -> None:
    with pytest.raises(PrecommitError), ModifiablePrecommit.load(config) as precommit:
        _update_precommit_config(precommit)


def test_update_precommit_config(tmp_path: Path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text(
        dedent("""
        repos:
          - repo: meta
            hooks:
              - id: check-hooks-apply
        """).lstrip()
    )
    _run_update(config)
    expected = dedent("""
        repos:
          - repo: meta
            hooks:
              - id: check-hooks-apply

          - repo: https://github.com/astral-sh/ty-pre-commit
            rev: PLEASE-UPDATE
            hooks:
              - id: ty
                args: [--no-progress, --output-format=concise]
                types_or: [python, pyi, jupyter]
        """).lstrip()
    assert config.read_text() == expected


def test_update_precommit_config_migrates_local_hook(tmp_path: Path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text(
        dedent("""
        repos:
          - repo: local
            hooks:
              - id: ty
                name: ty
                entry: ty check
                args: [--no-progress, --output-format=concise]
                language: system
                require_serial: true
                types_or: [python, pyi, jupyter]
                exclude: docs/.*
        """).lstrip()
    )
    _run_update(config)
    result = config.read_text()
    assert "repo: local" not in result
    assert "https://github.com/astral-sh/ty-pre-commit" in result
    assert "entry: ty check" not in result
    assert "language: system" not in result
    assert "exclude: docs/.*" in result
