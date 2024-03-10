from pathlib import Path

import pytest

from compwa_policy.check_dev_files.cspell import _update_cspell_repo_url
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.precommit import ModifiablePrecommit, Precommit


def test_update_cspell_repo_url():
    test_dir = Path(__file__).parent / "cspell"
    with pytest.raises(
        PrecommitError, match=r"Updated cSpell pre-commit repo URL"
    ), ModifiablePrecommit.load(test_dir / ".pre-commit-config-bad.yaml") as bad:
        _update_cspell_repo_url(bad)

    good_config = Precommit.load(test_dir / ".pre-commit-config-good.yaml")
    imported = good_config.document["repos"][0]["repo"]
    expected = bad.document["repos"][0]["repo"]
    assert imported == expected
