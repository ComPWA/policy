"""Characterization of repository."""

from functools import cache

from compwa_policy.utilities.match import is_committed


@cache
def has_documentation() -> bool:
    if is_committed("docs/**"):
        return True
    if is_committed("**/_quarto.yml"):
        return True
    return is_committed("**/conf.py")


@cache
def has_python_code() -> bool:
    return is_committed("**/*.ipynb", "**/*.py", "**/*.pyi")
