import io
from textwrap import dedent

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.format.cspell import _update_cspell_repo_url
from compwa_policy.utilities.precommit import ModifiablePrecommit


def test_update_cspell_repo_url():
    bad_config = dedent("""
        repos:
          - repo: https://github.com/ComPWA/mirrors-cspell
            rev: v5.10.1
            hooks:
              - id: cspell
    """).lstrip()
    with (
        pytest.raises(PrecommitError, match=r"Updated cSpell pre-commit repo URL"),
        ModifiablePrecommit.load(io.StringIO(bad_config)) as precommit,
    ):
        _update_cspell_repo_url(precommit)

    repo_url = precommit.document["repos"][0]["repo"]
    assert repo_url == "https://github.com/streetsidesoftware/cspell-cli"
