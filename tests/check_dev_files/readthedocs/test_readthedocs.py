from __future__ import annotations

import io
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from compwa_policy.check_dev_files import readthedocs
from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION
from compwa_policy.errors import PrecommitError

if TYPE_CHECKING:
    from compwa_policy.utilities.pyproject.getters import PythonVersion


@pytest.fixture
def this_dir() -> Path:
    return Path(__file__).parent


def test_update_readthedocs_extend(this_dir: Path):
    with open(this_dir / "extend" / ".readthedocs-bad.yml") as f:
        input_stream = io.StringIO(f.read())
    with pytest.raises(PrecommitError) as exception:
        readthedocs.main(
            "conda",
            python_version=DEFAULT_DEV_PYTHON_VERSION,
            source=input_stream,
        )

    exception_msg = dedent(f"""
      Updated .readthedocs.yml:
        - Set build.os to ubuntu-24.04
        - Set build.tools.python to {DEFAULT_DEV_PYTHON_VERSION!r}
        - Updated pip install steps
    """)
    assert str(exception.value).strip() == exception_msg.strip()

    with open(this_dir / "extend" / ".readthedocs-good.yml") as f:
        expected_output = f.read()
    input_stream.seek(0)
    result = input_stream.read()
    assert result.strip() == expected_output.strip()


@pytest.mark.parametrize("example", ["extend", "overwrite"])
def test_update_readthedocs_good(this_dir: Path, example: str):
    with open(this_dir / example / ".readthedocs-good.yml") as f:
        input_stream = io.StringIO(f.read())
    readthedocs.main(
        "conda",
        python_version=DEFAULT_DEV_PYTHON_VERSION,
        source=input_stream,
    )

    with open(this_dir / example / ".readthedocs-good.yml") as f:
        expected_output = f.read()
    input_stream.seek(0)
    result = input_stream.read()
    assert result.strip() == expected_output.strip()


@pytest.mark.parametrize("python_version", ["3.9", "3.10"])
@pytest.mark.parametrize("suffix", ["bad1", "bad2"])
def test_update_readthedocs_overwrite(
    this_dir: Path, python_version: PythonVersion, suffix: str
):
    with open(this_dir / "overwrite" / f".readthedocs-{suffix}.yml") as f:
        input_stream = io.StringIO(f.read())
    with pytest.raises(PrecommitError) as exception:
        readthedocs.main("conda", python_version, source=input_stream)

    exception_msg = dedent(f"""
      Updated .readthedocs.yml:
        - Set build.os to ubuntu-24.04
        - Set build.tools.python to {python_version!r}
        - Updated pip install steps
    """)
    assert str(exception.value).strip() == exception_msg.strip()

    with open(this_dir / "overwrite" / ".readthedocs-good.yml") as f:
        expected_output = f.read()
    expected_output = expected_output.replace(
        DEFAULT_DEV_PYTHON_VERSION, python_version
    )
    input_stream.seek(0)
    result = input_stream.read()
    assert result.strip() == expected_output.strip()
