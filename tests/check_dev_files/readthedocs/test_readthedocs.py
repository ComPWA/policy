import io
from pathlib import Path
from textwrap import dedent

import pytest

from compwa_policy.check_dev_files import readthedocs
from compwa_policy.errors import PrecommitError


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


def test_update_readthedocs(this_dir: Path):
    with open(this_dir / ".readthedocs-bad.yml") as f:
        input_stream = io.StringIO(f.read())
    with pytest.raises(PrecommitError) as exception:
        readthedocs.main(python_version="3.9", source=input_stream)

    exception_msg = dedent("""
      Updated .readthedocs.yml:
        - Set build.os to ubuntu-22.04
        - Set build.tools.python to '3.9'
        - Updated pip install steps
    """)
    assert str(exception.value).strip() == exception_msg.strip()

    with open(this_dir / ".readthedocs-good.yml") as f:
        expected_output = f.read()
    input_stream.seek(0)
    result = input_stream.read()
    assert result.strip() == expected_output.strip()
