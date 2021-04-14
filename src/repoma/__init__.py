"""Bundled developer configurations and tools for ComPWA repositories.

This package contains `pre-commit <https://pre-commit.com>` hooks that the
`ComPWA repositories <https://github.com/ComPWA>` have in common.
"""

__all__ = [
    "pre_commit_hooks",
]

from . import pre_commit_hooks
