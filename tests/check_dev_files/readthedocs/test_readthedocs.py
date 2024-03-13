from __future__ import annotations

import io
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from compwa_policy.check_dev_files import readthedocs
from compwa_policy.errors import PrecommitError

if TYPE_CHECKING:
    from compwa_policy.utilities.pyproject.getters import PythonVersion


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


@pytest.mark.parametrize("python_version", ["3.9", "3.10"])
@pytest.mark.parametrize("suffix", ["bad1", "bad2"])
def test_update_readthedocs(this_dir: Path, python_version: PythonVersion, suffix: str):
    with open(this_dir / f".readthedocs-{suffix}.yml") as f:
        input_stream = io.StringIO(f.read())
    with pytest.raises(PrecommitError) as exception:
        readthedocs.main(python_version, source=input_stream)

    exception_msg = dedent(f"""
      Updated .readthedocs.yml:
        - Set build.os to ubuntu-22.04
        - Set build.tools.python to {python_version!r}
        - Updated pip install steps
    """)
    assert str(exception.value).strip() == exception_msg.strip()

    with open(this_dir / ".readthedocs-good.yml") as f:
        expected_output = f.read()
    expected_output = expected_output.replace("3.9", python_version)
    input_stream.seek(0)
    result = input_stream.read()
    assert result.strip() == expected_output.strip()
