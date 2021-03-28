"""Bundled developer configurations and tools for ComPWA repositories.

This package contains `pre-commit <https://pre-commit.com>` hooks that the
`ComPWA repositories <https://github.com/ComPWA>` have in common.
"""

__all__ = [
    "dev_tools",
    "pre_commit_hooks",
]

from . import dev_tools, pre_commit_hooks
