import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pytest_benchmark.fixture import BenchmarkFixture


@pytest.mark.benchmark(group="check-dev-files", min_rounds=5)
def test_check_dev_files(benchmark: BenchmarkFixture) -> None:
    target = _get_benchmark_target()
    executable = shutil.which("check-dev-files")
    if executable is None:
        msg = "Could not find the check-dev-files executable"
        raise RuntimeError(msg)
    environment = {**os.environ, "COMPWA_POLICY_DEBUG": "0"}

    result = benchmark(
        subprocess.run,
        [executable],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def _get_benchmark_target() -> Path:
    value = os.getenv("COMPWA_POLICY_BENCHMARK_TARGET")
    if value is None:
        pytest.skip("COMPWA_POLICY_BENCHMARK_TARGET is not configured")
    target = Path(value).resolve()
    if not (target / ".git").exists():
        msg = (
            f"Benchmark target {target} is not a Git repository. Check out "
            "ComPWA/ampform there or set COMPWA_POLICY_BENCHMARK_TARGET."
        )
        raise RuntimeError(msg)
    return target
