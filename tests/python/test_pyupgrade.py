import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.pyupgrade import _remove_pyupgrade, main
from compwa_policy.utilities.precommit import ModifiablePrecommit


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


@pytest.mark.usefixtures("_project_with_classifiers")
def test_main_installs_pyupgrade():
    config = dedent("""
        repos:
          - repo: https://github.com/nbQA-dev/nbQA
            rev: 1.8.5
            hooks:
              - id: nbqa-isort
    """).lstrip()
    with (
        pytest.raises(PrecommitError),
        ModifiablePrecommit.load(io.StringIO(config)) as precommit,
    ):
        main(precommit, no_ruff=True)

    result = precommit.dumps()
    assert "https://github.com/asottile/pyupgrade" in result
    assert "--py310-plus" in result
    assert "nbqa-pyupgrade" in result


def test_main_removes_pyupgrade_when_ruff_is_used():
    config = dedent("""
        repos:
          - repo: https://github.com/asottile/pyupgrade
            rev: v3.15.0
            hooks:
              - id: pyupgrade
                args: [--py310-plus]
    """).lstrip()
    with (
        pytest.raises(PrecommitError, match=r"pyupgrade"),
        ModifiablePrecommit.load(io.StringIO(config)) as precommit,
    ):
        main(precommit, no_ruff=False)

    assert "pyupgrade" not in precommit.dumps()


def test_remove_pyupgrade_also_removes_nbqa_hook():
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
    with (
        pytest.raises(PrecommitError),
        ModifiablePrecommit.load(io.StringIO(config)) as precommit,
    ):
        _remove_pyupgrade(precommit)

    assert "pyupgrade" not in precommit.dumps()
