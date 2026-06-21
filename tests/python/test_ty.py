import io
from pathlib import Path

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.python.ty import _update_precommit_config
from compwa_policy.utilities.precommit import ModifiablePrecommit


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


def test_update_precommit_config(this_dir: Path):
    with open(this_dir / ".pre-commit-config-bad.yaml") as stream:
        input_stream = io.StringIO(stream.read())
    with (
        pytest.raises(PrecommitError),
        ModifiablePrecommit.load(input_stream) as precommit,
    ):
        _update_precommit_config(precommit)

    result = input_stream.getvalue()
    with open(this_dir / ".pre-commit-config-good.yaml") as stream:
        expected_result = stream.read()
    assert result.strip() == expected_result.strip()


def test_update_precommit_config_migrates_local_hook(tmp_path: Path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text(
        "repos:\n"
        "  - repo: local\n"
        "    hooks:\n"
        "      - id: ty\n"
        "        name: ty\n"
        "        entry: ty check\n"
        "        args: [--no-progress, --output-format=concise]\n"
        "        language: system\n"
        "        require_serial: true\n"
        "        types_or: [python, pyi, jupyter]\n"
        "        exclude: docs/.*\n"
    )
    with pytest.raises(PrecommitError), ModifiablePrecommit.load(config) as precommit:
        _update_precommit_config(precommit)

    result = config.read_text()
    assert "repo: local" not in result
    assert "https://github.com/astral-sh/ty-pre-commit" in result
    assert "entry: ty check" not in result
    assert "language: system" not in result
    assert "exclude: docs/.*" in result
