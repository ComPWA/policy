"""Contract for transformations run by :program:`check-dev-files`."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal

from attrs import frozen

from compwa_policy import Arguments
from compwa_policy.utilities.session import Session

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


Group = Literal["python", "github", "env", "nb", "format", "repo"]


@frozen
class FileSet:
    """Paths whose staged modification should activate a check hook.

    Directories match every file below them. Patterns are regular-expression
    alternatives for path families that cannot be expressed as one exact path.
    """

    paths: tuple[Path, ...] = ()
    directories: tuple[Path, ...] = ()
    patterns: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *paths: Path | str,
        directories: Iterable[Path | str] = (),
        patterns: Iterable[str] = (),
    ) -> Self:
        return cls(
            paths=tuple(Path(path) for path in paths),
            directories=tuple(Path(path) for path in directories),
            patterns=tuple(patterns),
        )

    @classmethod
    def union(cls, file_sets: tuple[FileSet, ...]) -> Self:
        paths = dict.fromkeys(path for files in file_sets for path in files.paths)
        directories = dict.fromkeys(
            path for files in file_sets for path in files.directories
        )
        patterns = dict.fromkeys(
            pattern for files in file_sets for pattern in files.patterns
        )
        return cls(tuple(paths), tuple(directories), tuple(patterns))

    def to_regex(self) -> str:
        directory_patterns = tuple(
            rf"{re.escape(path.as_posix())}/.*" for path in self.directories
        )
        file_patterns = tuple(
            re.escape(path.as_posix())
            for path in self.paths
            if not any(path.is_relative_to(directory) for directory in self.directories)
        )
        alternatives = sorted(
            {*directory_patterns, *file_patterns, *self.patterns},
            key=str.casefold,
        )
        lines = [
            f"  {pattern}{'|' if i < len(alternatives) - 1 else ''}"
            for i, pattern in enumerate(alternatives)
        ]
        return "(?x)^(\n" + "\n".join(lines) + "\n)$"


@frozen
class CheckContext:
    """Repository properties that are derived once and shared by every check."""

    is_python_repo: bool
    has_notebooks: bool
    doc_apt_packages: list[str]
    environment_variables: dict[str, str]


def _always_enabled(_args: Arguments, _ctx: CheckContext) -> bool:
    return True


Check = Callable[[Session, Arguments, CheckContext], None]


@frozen
class CheckHook:
    """One policy transformation together with its dispatch metadata."""

    group: Group
    files: FileSet
    run: Check
    enabled: Callable[[Arguments, CheckContext], bool] = _always_enabled

    def __call__(
        self,
        session: Session,
        args: Arguments,
        context: CheckContext,
    ) -> None:
        if self.enabled(args, context):
            self.run(session, args, context)


def check_hook(
    *,
    group: Group,
    paths: Iterable[Path | str] = (),
    directories: Iterable[Path | str] = (),
    patterns: Iterable[str] = (),
    enabled: Callable[[Arguments, CheckContext], bool] = _always_enabled,
) -> Callable[[Check], CheckHook]:
    """Attach dispatch and trigger metadata to a ``check`` function."""

    def register(run: Check) -> CheckHook:
        return CheckHook(group, files, run, enabled)

    files = FileSet.create(
        *paths,
        directories=directories,
        patterns=patterns,
    )
    return register
