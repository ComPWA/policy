"""Functions for checking whether files exist on disk."""

from __future__ import annotations

import subprocess  # noqa: S404

from pathspec import PathSpec


def filter_files(patterns: list[str], files: list[str] | None = None) -> list[str]:
    """Filter filenames that match certain patterns.

    If :code:`files` is not supplied, get the files with :func:`git_ls_files`.

    >>> filter_files(["**/*.json", "**/*.txt"], ["a/b/file.json", "file.yaml"])
    ['a/b/file.json']
    """
    if files is None:
        files = git_ls_files(untracked=True)
    return [file for file in files if matches_patterns(file, patterns)]


def filter_patterns(patterns: list[str], files: list[str] | None = None) -> list[str]:
    """Filter patterns that match files.

    If :code:`files` is not supplied, get the files with :func:`git_ls_files`.

    >>> filter_patterns(["**/*.json", "**/*.txt"], ["file.json", "file.yaml"])
    ['**/*.json']
    """
    if files is None:
        files = git_ls_files(untracked=True)
    return [pattern for pattern in patterns if matches_files(pattern, files)]


def git_ls_files(untracked: bool = False) -> list[str]:
    """Get the tracked and untracked files, but excluding files in .gitignore."""
    output = subprocess.check_output([  # noqa: S607
        "git",
        "ls-files",
    ]).decode("utf-8")
    tracked_files = output.splitlines()
    if untracked:
        output = subprocess.check_output([  # noqa: S607
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
        ]).decode("utf-8")
        return tracked_files + output.splitlines()
    return tracked_files


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


def matches_patterns(filename: str, patterns: list[str]) -> bool:
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
