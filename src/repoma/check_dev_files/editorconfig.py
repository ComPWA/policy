"""Check existence of pre-commit hook for EditorConfig.

If a repository has an ``.editorconfig`` file, it should have an `EditorConfig
pre-commit hook
<https://github.com/editorconfig-checker/editorconfig-checker.python>`_.
"""

from textwrap import dedent

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, FoldedScalarString

from repoma.utilities import CONFIG_PATH
from repoma.utilities.precommit import update_single_hook_precommit_repo


def main() -> None:
    if CONFIG_PATH.editorconfig.exists():
        _update_precommit_config()


def _update_precommit_config() -> None:
    excludes = dedent(R"""
    (?x)^(
      .*\.py
    )$
    """).strip()
    expected_hook = CommentedMap(
        repo="https://github.com/editorconfig-checker/editorconfig-checker.python",
        rev=DoubleQuotedScalarString(""),
        hooks=[
            CommentedMap(
                id="editorconfig-checker",
                name="editorconfig",
                alias="ec",
                exclude=FoldedScalarString(excludes),
            )
        ],
    )
    update_single_hook_precommit_repo(expected_hook)
