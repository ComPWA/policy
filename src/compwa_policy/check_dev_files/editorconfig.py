"""Check existence of pre-commit hook for EditorConfig.

If a repository has an ``.editorconfig`` file, it should have an `EditorConfig
pre-commit hook
<https://github.com/editorconfig-checker/editorconfig-checker.python>`_.
"""

from textwrap import dedent

from ruamel.yaml.scalarstring import FoldedScalarString

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    update_single_hook_precommit_repo,
)


def main(no_python: bool) -> None:
    if CONFIG_PATH.editorconfig.exists():
        _update_precommit_config(no_python)


def _update_precommit_config(no_python: bool) -> None:
    hook = Hook(
        id="editorconfig-checker",
        name="editorconfig",
        alias="ec",
    )
    if not no_python:
        msg = R"""
        (?x)^(
          .*\.py
        )$
        """
        excludes = dedent(msg).strip()
        hook["exclude"] = FoldedScalarString(excludes)

    expected_hook = Repo(
        repo="https://github.com/editorconfig-checker/editorconfig-checker.python",
        rev="",
        hooks=[hook],
    )
    update_single_hook_precommit_repo(expected_hook)
