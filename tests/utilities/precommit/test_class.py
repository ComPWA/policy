import io
from pathlib import Path

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.precommit import ModifiablePrecommit, Precommit


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture
def example_config(this_dir: Path) -> str:
    with open(this_dir / ".pre-commit-config.yaml") as file:
        return file.read()


def describe_modifiable_precommit():
    def rejects_changes_outside_context_manager(example_config: str):
        precommit = ModifiablePrecommit.load(example_config)
        precommit.document["fail_fast"] = True
        with pytest.raises(
            expected_exception=RuntimeError,
            match=r"^Modifications can only be made within a context$",
        ):
            precommit.changelog.append("Fake modification")

    def restores_path_source_on_change(example_config: str):
        input_stream = io.StringIO(example_config)
        with (
            pytest.raises(PrecommitError, match=r"Fake modification$"),
            ModifiablePrecommit.load(input_stream) as precommit,
        ):
            precommit.changelog.append("Fake modification")
        yaml = precommit.dumps()
        assert yaml == example_config

    def writes_back_to_string_stream(example_config: str):
        stream = io.StringIO(example_config)
        with (
            pytest.raises(PrecommitError, match=r"Fake modification$"),
            ModifiablePrecommit.load(stream) as precommit,
        ):
            precommit.changelog.append("Fake modification")
        stream.seek(0)
        yaml = stream.read()
        assert yaml == example_config


def describe_precommit():
    def dumps_round_trips_config(this_dir: Path, example_config: str):
        precommit = Precommit.load(this_dir / ".pre-commit-config.yaml")
        yaml = precommit.dumps()
        assert yaml == example_config
