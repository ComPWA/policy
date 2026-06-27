import io
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.format.editorconfig import _update_precommit_config
from compwa_policy.utilities.precommit import ModifiablePrecommit


def describe_update_precommit_config():
    def configures_editorconfig_checker_hook():
        bad_config = dedent("""
            repos:
              - repo: https://github.com/editorconfig-checker/editorconfig-checker.python
                rev: 2.7.3
                hooks:
                  - id: editorconfig-checker
        """).lstrip()
        with (
            pytest.raises(PrecommitError, match=r"Updated editorconfig-checker hook"),
            ModifiablePrecommit.load(io.StringIO(bad_config)) as precommit,
        ):
            _update_precommit_config(precommit)

        expected = dedent(r"""
            repos:
              - repo: https://github.com/editorconfig-checker/editorconfig-checker.python
                rev: 2.7.3
                hooks:
                  - id: editorconfig-checker
                    name: editorconfig
                    alias: ec
                    exclude: >-
                      (?x)^(
                        .*\.py
                      )$
        """).lstrip()
        assert precommit.dumps() == expected
