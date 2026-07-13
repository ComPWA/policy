"""Common interface for mutable, file-backed policy resources."""

from __future__ import annotations

import os
import shutil
import sys
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
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

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _tb: TracebackType | None,
    ) -> bool:
        return False


class ModifiableConfigFiles(ModifiableResource):
    """A deferred set of standalone config paths to remove on flush."""

    def __init__(self) -> None:
        self._paths: list[str] = []
        self._changelog: Changelog = []

    @classmethod
    def load(cls) -> Self:
        return cls()

    @property
    def changelog(self) -> Changelog:
        return self._changelog

    def remove(self, paths: list[str]) -> None:
        for path in paths:
            if path in self._paths or not os.path.exists(path):
                continue
            self._paths.append(path)
            self._changelog.append(f"Removed {path}")

    def dump(self) -> None:
        for path in self._paths:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
