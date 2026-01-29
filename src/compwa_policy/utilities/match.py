"""Functions for checking whether files exist on disk."""

from __future__ import annotations

import subprocess  # noqa: S404
from functools import cache
from typing import TYPE_CHECKING

from pathspec import PathSpec

if TYPE_CHECKING:
    from collections.abc import Iterable


def filter_patterns(patterns: list[str], files: list[str] | None = None) -> list[str]:
    """Filter patterns that match files.

    If :code:`files` is not supplied, get the files with :func:`git_ls_files`.

    >>> filter_patterns(["**/*.json", "**/*.txt"], ["file.json", "file.yaml"])
    ['**/*.json']
    """
    if files is None:
        files = git_ls_files(untracked=True)
    return [pattern for pattern in patterns if matches_files(pattern, files)]


def git_ls_files(*glob: str, untracked: bool = False) -> list[str]:
    """Get the tracked and untracked files, but excluding files in .gitignore."""
    output = _git_ls_files_cmd(*glob, untracked=untracked)
    return output.splitlines()


def is_committed(*glob: str, untracked: bool = False) -> bool:
    """Check if any files matching the given git wild-match patterns are committed."""
    return bool(_git_ls_files_cmd(*glob, untracked=untracked))


@cache
def _git_ls_files_cmd(*glob: str, untracked: bool = False) -> str:
    cmd = ["git", "ls-files", *glob]
    if untracked:
        cmd.extend(["--cached", "--exclude-standard", "--others"])
    return subprocess.check_output(cmd).decode("utf-8")  # noqa: S603


def matches_files(pattern: str, files: list[str]) -> bool:
    """Use git wild-match patterns to match a filename.

    >>> matches_files("**/*.json", [".cspell.json"])
    True
    >>> matches_files("**/*.json", ["some/random/path/.cspell.json"])
    True
    >>> matches_files("*/*.json", ["some/random/path/.cspell.json"])
    False
    """
    spec = PathSpec.from_lines("gitignore", [pattern])
    return any(spec.match_file(file) for file in files)


def matches_patterns(filename: str, patterns: Iterable[str]) -> bool:
    """Use git wild-match patterns to match a filename.

    >>> matches_patterns(".cspell.json", patterns=["**/*.json"])
    True
    >>> matches_patterns("some/random/path/.cspell.json", patterns=["**/*.json"])
    True
    >>> matches_patterns("some/random/path/.cspell.json", patterns=["*/*.json"])
    False
    """
    spec = PathSpec.from_lines("gitignore", patterns)
    return spec.match_file(filename)
