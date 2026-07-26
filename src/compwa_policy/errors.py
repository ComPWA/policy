# ruff: ignore[undocumented-public-module]
class PolicyError(RuntimeError):
    """Policy violation that is caught by the executor and printed without a traceback."""
