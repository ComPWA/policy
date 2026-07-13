"""Common interface for mutable, file-backed policy resources."""

from __future__ import annotations

import shutil
import sys
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
if TYPE_CHECKING:
    from types import TracebackType

    from compwa_policy.utilities.session import Session


ChangelogItem: TypeAlias = str
"""A user-facing message that describes one policy change."""

Changelog: TypeAlias = list[ChangelogItem]
"""Messages reported by a policy check."""

_ACTIVE_SESSION: ContextVar[Session | None] = ContextVar("active_session", default=None)


def get_active_session() -> Session | None:
    return _ACTIVE_SESSION.get()


def activate_session(session: Session) -> Token[Session | None]:
    return _ACTIVE_SESSION.set(session)


def deactivate_session(token: Token[Session | None]) -> None:
    _ACTIVE_SESSION.reset(token)


class ModifiableResource(AbstractContextManager, ABC):
    """A file loaded once and written once after in-memory modification."""

    @classmethod
    @abstractmethod
    def load(cls) -> Self:
        """Load the resource from the working tree."""

    @property
    @abstractmethod
    def changelog(self) -> Changelog:
        """Changes made to the in-memory representation."""

    @abstractmethod
    def dump(self) -> None:
        """Write the in-memory representation to the working tree."""

    @property
    def changed(self) -> bool:
        """Whether the resource needs to be flushed."""
        return bool(self.changelog)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _tb: TracebackType | None,
    ) -> bool:
        return False


class ModifiablePath(ModifiableResource):
    """Deferred in-memory state for one arbitrary working-tree path."""

    def __init__(
        self,
        path: Path,
        content: bytes | None,
        *,
        is_directory: bool = False,
    ) -> None:
        self.path = path
        self._original_content = content
        self._content = content
        self._is_directory = is_directory
        self._original_is_directory = is_directory
        self._changelog: Changelog = []

    @classmethod
    def load(cls) -> Self:
        msg = "ModifiablePath requires a path identity"
        raise TypeError(msg)

    @classmethod
    def load_path(cls, path: Path | str) -> Self:
        path = Path(path)
        if path.is_dir():
            return cls(path, None, is_directory=True)
        if path.exists():
            return cls(path, path.read_bytes())
        return cls(path, None)

    @property
    def changelog(self) -> Changelog:
        return self._changelog

    @property
    def changed(self) -> bool:
        return (
            self._content != self._original_content
            or self._is_directory != self._original_is_directory
        )

    @property
    def exists(self) -> bool:
        return self._is_directory or self._content is not None

    def read_text(self) -> str:
        if self._content is None:
            msg = f"{self.path} does not exist or is a directory"
            raise FileNotFoundError(msg)
        return self._content.decode()

    def write_text(self, content: str, message: str | None = None) -> bool:
        encoded = content.encode()
        if not self._is_directory and self._content == encoded:
            return False
        self._content = encoded
        self._is_directory = False
        if message is not None:
            self._changelog.append(message)
        return True

    def remove(self, message: str | None = None) -> bool:
        if not self.exists:
            return False
        self._content = None
        self._is_directory = False
        if message is not None:
            self._changelog.append(message)
        return True

    def dump(self) -> None:
        if not self.exists:
            if self.path.is_dir():
                shutil.rmtree(self.path)
            else:
                self.path.unlink(missing_ok=True)
            return
        if not self.changed:
            return
        self.path.parent.mkdir(exist_ok=True, parents=True)
        self.path.write_bytes(self._content or b"")
