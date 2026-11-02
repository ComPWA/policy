from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.python.docstrfmt import check
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.session import Session


def describe_check():
    @pytest.mark.parametrize(
        "hook_options",
        [
            "types: [python]",
            "types_or: [python]",
            "files: ^src/",
        ],
    )
    def removes_file_type_overrides(run_check, tmp_path: Path, hook_options: str):
        path = tmp_path / ".pre-commit-config.yaml"
        path.write_text(
            dedent(f"""
            repos:
              - repo: https://github.com/LilSpazJoekp/docstrfmt
                rev: v2.2.1
                hooks:
                  - id: docstrfmt
                    {hook_options}
            """).lstrip()
        )
        precommit = ModifiablePrecommit.load(path)
        with Session.load(precommit) as session:
            run_check(check, session)

        assert precommit.changelog
        result = precommit.dumps()
        assert hook_options not in result
        assert "rev: v2.2.1" in result

    def does_not_add_hook(run_check, tmp_path: Path):
        path = tmp_path / ".pre-commit-config.yaml"
        path.write_text(
            dedent("""
            repos:
              - repo: https://github.com/pre-commit/pre-commit-hooks
                rev: v6.0.0
                hooks:
                  - id: check-yaml
            """).lstrip()
        )
        precommit = ModifiablePrecommit.load(path)
        with Session.load(precommit) as session:
            run_check(check, session)

        assert not precommit.changelog
        assert "docstrfmt" not in precommit.dumps()
