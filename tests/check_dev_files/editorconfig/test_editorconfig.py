import io
from pathlib import Path

import pytest

from compwa_policy.check_dev_files.editorconfig import _update_precommit_config
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.precommit import ModifiablePrecommit


@pytest.mark.parametrize("no_python", [True, False])
def test_update_precommit_config(no_python: bool):
    this_dir = Path(__file__).parent
    with open(this_dir / ".pre-commit-config-bad.yaml") as file:
        src = file.read()

    stream = io.StringIO(src)
    with pytest.raises(
        PrecommitError, match=r"Updated editorconfig-checker hook"
    ), ModifiablePrecommit.load(stream) as precommit:
        _update_precommit_config(precommit, no_python)

    result = precommit.dumps()
    if no_python:
        expected_file = this_dir / ".pre-commit-config-good-no-python.yaml"
    else:
        expected_file = this_dir / ".pre-commit-config-good.yaml"
    with open(expected_file) as file:
        expected = file.read()
    assert result == expected
