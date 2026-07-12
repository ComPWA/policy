import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pytest_benchmark.fixture import BenchmarkFixture


@pytest.mark.benchmark(group="check-dev-files", min_rounds=5)
def test_check_dev_files(
    benchmark: BenchmarkFixture,
    benchmark_target: Path,
) -> None:
    executable = shutil.which("check-dev-files")
    if executable is None:
        msg = "Could not find the check-dev-files executable"
        raise RuntimeError(msg)
    environment = {**os.environ, "COMPWA_POLICY_DEBUG": "0"}

    result = benchmark(
        subprocess.run,
        [executable],
        cwd=benchmark_target,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
