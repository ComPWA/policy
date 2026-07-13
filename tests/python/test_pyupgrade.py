import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.python.pyupgrade import _remove_pyupgrade, check
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session


@pytest.fixture
def _project_with_classifiers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
        [project]
        name = "my-package"
        classifiers = [
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
        ]
        """).lstrip()
    )


def describe_main():
    @pytest.mark.usefixtures("_project_with_classifiers")
    def installs_pyupgrade(run_check):
        config = dedent("""
            repos:
              - repo: https://github.com/nbQA-dev/nbQA
                rev: 1.8.5
                hooks:
                  - id: nbqa-isort
        """).lstrip()
        precommit = ModifiablePrecommit.load(io.StringIO(config))
        with Session.load(precommit) as session:
            run_check(check, session, no_ruff=True)

        assert precommit.changelog  # something changed
        result = precommit.dumps()
        assert "https://github.com/asottile/pyupgrade" in result
        assert "--py310-plus" in result
        assert "nbqa-pyupgrade" in result

    def removes_pyupgrade_when_ruff_is_used(run_check):
        config = dedent("""
            repos:
              - repo: https://github.com/asottile/pyupgrade
                rev: v3.15.0
                hooks:
                  - id: pyupgrade
                    args: [--py310-plus]
        """).lstrip()
        precommit = ModifiablePrecommit.load(io.StringIO(config))
        with Session.load(precommit) as session:
            run_check(check, session, no_ruff=False)

        assert any("pyupgrade" in m for m in precommit.changelog)
        assert "pyupgrade" not in precommit.dumps()


def describe_remove_pyupgrade():
    def also_removes_nbqa_hook():
        config = dedent("""
            repos:
              - repo: https://github.com/asottile/pyupgrade
                rev: v3.15.0
                hooks:
                  - id: pyupgrade
              - repo: https://github.com/nbQA-dev/nbQA
                rev: 1.8.5
                hooks:
                  - id: nbqa-pyupgrade
        """).lstrip()
        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            _remove_pyupgrade(precommit)

        assert precommit.changelog  # something was removed
        assert "pyupgrade" not in precommit.dumps()
