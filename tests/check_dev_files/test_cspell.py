import io
from pathlib import Path

import pytest

from compwa_policy.check_dev_files.cspell import _update_cspell_repo_url
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.precommit import ModifiablePrecommit, Precommit


def test_update_cspell_repo_url(bad_yaml: io.StringIO, good_yaml: io.StringIO):
    with pytest.raises(
        PrecommitError, match=r"Updated cSpell pre-commit repo URL"
    ), ModifiablePrecommit.load(bad_yaml) as bad:
        _update_cspell_repo_url(bad)

    good = Precommit.load(good_yaml)
    imported = good.document["repos"][0]["repo"]
    expected = bad.document["repos"][0]["repo"]
    assert imported == expected


@pytest.fixture(scope="module")
def bad_yaml() -> io.StringIO:
    return load_config(".pre-commit-config-bad.yaml")


@pytest.fixture(scope="module")
def good_yaml() -> io.StringIO:
    return load_config(".pre-commit-config-good.yaml")


def load_config(filename: str) -> io.StringIO:
    path = Path(__file__).parent / "cspell" / filename
    with path.open() as file:
        return io.StringIO(file.read())
