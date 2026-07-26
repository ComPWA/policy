from __future__ import annotations

import io
from textwrap import dedent
from typing import TYPE_CHECKING, cast

from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.precommit.struct import Hook, Repo

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap, CommentedSeq


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


def describe_update_precommit_hook():
    def appends_hook_to_repo_with_fewer_repos_than_hooks():
        """The separator used to be keyed on the hook index, not the repo index.

        Indexing ``repos`` with a hook index raises `IndexError` as soon as the
        hook lands beyond the last repo.
        """
        config = dedent("""
            repos:
              - repo: meta
                hooks:
                  - id: check-hooks-apply

              - repo: https://github.com/nbQA-dev/nbQA
                rev: 1.9.1
                hooks:
                  - id: nbqa-black
                  - id: nbqa-isort
        """).lstrip()

        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            precommit.update_hook(
                "https://github.com/nbQA-dev/nbQA", Hook(id="nbqa-pyupgrade")
            )

        assert "id: nbqa-pyupgrade" in precommit.dumps()

    def sets_the_separator_on_the_repo_sequence():
        config = dedent("""
            repos:
              - repo: https://github.com/nbQA-dev/nbQA
                rev: 1.9.1
                hooks:
                  - id: nbqa-isort

              - repo: meta
                hooks:
                  - id: check-hooks-apply
        """).lstrip()

        with ModifiablePrecommit.load(io.StringIO(config)) as precommit:
            precommit.update_hook(
                "https://github.com/nbQA-dev/nbQA", Hook(id="nbqa-pyupgrade")
            )
            repos = cast("CommentedSeq", precommit.document["repos"])
            first_repo = cast("CommentedMap", repos[0])
            assert 1 in repos.ca.items  # separator before the next repo
            assert not any(isinstance(key, int) for key in first_repo.ca.items)
