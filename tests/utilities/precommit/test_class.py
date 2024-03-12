from pathlib import Path

import pytest

from compwa_policy.utilities.precommit import Precommit


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


class TestPrecommit:
    def test_dumps(self, this_dir: Path):
        precommit = Precommit.load(this_dir / ".pre-commit-config.yaml")
        yaml = precommit.dumps()
        with open(this_dir / ".pre-commit-config.yaml") as file:
            expected = file.read()
        assert yaml == expected
