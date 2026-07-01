import io
from textwrap import dedent

from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.precommit.struct import Hook, Repo


def _expected_ty_repo() -> Repo:
    return Repo(
        repo="local",
        hooks=[
            Hook(
                id="ty",
                name="ty",
                entry="ty check",
                language="system",
            )
        ],
    )


def describe_update_single_hook_precommit_repo():
    def preserves_unrelated_local_repo_when_adding_managed_hook():
        config = dedent("""
            repos:
              - repo: local
                hooks:
                  - id: check-foo
                    name: check-foo
                    entry: check-foo
                    language: system
        """).lstrip()

        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            precommit.update_single_hook_repo(_expected_ty_repo())

        result = precommit.dumps()
        assert "id: check-foo" in result
        assert "id: ty" in result
        assert result.count("repo: local") == 2

    def updates_managed_local_hook_by_id():
        config = dedent("""
            repos:
              - repo: local
                hooks:
                  - id: check-foo
                    name: check-foo
                    entry: check-foo
                    language: system

              - repo: local
                hooks:
                  - id: ty
                    name: ty
                    entry: ty
                    language: system
        """).lstrip()

        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            precommit.update_single_hook_repo(_expected_ty_repo())

        result = precommit.dumps()
        assert "id: check-foo" in result
        assert "entry: ty check" in result
        assert result.count("id: ty") == 1

    def preserves_sibling_hooks_in_matching_local_repo():
        config = dedent("""
            repos:
              - repo: local
                hooks:
                  - id: check-foo
                    name: check-foo
                    entry: check-foo
                    language: system
                  - id: ty
                    name: ty
                    entry: ty
                    language: system
        """).lstrip()

        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            precommit.update_single_hook_repo(_expected_ty_repo())

        result = precommit.dumps()
        assert "id: check-foo" in result
        assert "entry: ty check" in result
        assert result.count("repo: local") == 1
