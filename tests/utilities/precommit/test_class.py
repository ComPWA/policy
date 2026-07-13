import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.utilities.precommit import ModifiablePrecommit, Precommit


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture
def example_config(this_dir: Path) -> str:
    with open(this_dir / ".pre-commit-config.yaml") as file:
        return file.read()


def describe_modifiable_precommit():
    def normalizes_spacing_between_and_within_repos(tmp_path: Path):
        source = tmp_path / ".pre-commit-config.yaml"
        input_yaml = dedent("""
          repos:
              - repo: first

              # Keep this comment.
                rev: "1"
                hooks:

                  - id: first

                  - id: second


              # Keep this repo comment.
              - repo: second
                hooks:
                  - id: third
              - repo: third
                hooks:
                  - id: fourth
        """).lstrip()
        expected = dedent("""
          repos:
            - repo: first
              # Keep this comment.
              rev: "1"
              hooks:
                - id: first
                - id: second

              # Keep this repo comment.
            - repo: second
              hooks:
                - id: third

            - repo: third
              hooks:
                - id: fourth
        """).lstrip()
        source.write_text(input_yaml)

        precommit = ModifiablePrecommit.load(source)
        precommit.dump(source)

        assert source.read_text() == expected

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
        with ModifiablePrecommit.load(input_stream) as precommit:
            precommit.changelog.append("Fake modification")
        yaml = precommit.dumps()
        assert yaml == example_config

    def writes_back_to_string_stream(example_config: str):
        stream = io.StringIO(example_config)
        with ModifiablePrecommit.load(stream) as precommit:
            precommit.changelog.append("Fake modification")
        stream.seek(0)
        yaml = stream.read()
        assert yaml == example_config


def describe_precommit():
    def dumps_round_trips_config(this_dir: Path, example_config: str):
        precommit = Precommit.load(this_dir / ".pre-commit-config.yaml")
        yaml = precommit.dumps()
        assert yaml == example_config
