from pathlib import Path

import pytest
from _pytest.config.argparsing import Parser


def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--benchmark-target", type=Path)


def pytest_configure(config: pytest.Config) -> None:
    target = config.getoption("benchmark_target")
    writes_benchmark_results = config.getoption(
        "benchmark_autosave"
    ) or config.getoption("benchmark_json")
    if writes_benchmark_results and target is None:
        msg = "benchmark mode requires --benchmark-target=PATH"
        raise pytest.UsageError(msg)


@pytest.fixture
def benchmark_target(request: pytest.FixtureRequest) -> Path:
    target: Path | None = request.config.getoption("benchmark_target")
    if target is None:
        pytest.skip("--benchmark-target is not configured")
    target = target.resolve()
    if not (target / ".git").exists():
        msg = (
            f"Benchmark target {target} is not a Git repository. Check out "
            "ComPWA/ampform there or pass its location with --benchmark-target."
        )
        raise RuntimeError(msg)
    return target
