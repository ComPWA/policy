"""In-memory view of the files that :program:`check-dev-files` inspects and modifies.

The `Session` follows the `Unit of Work
<https://martinfowler.com/eaaCatalog/unitOfWork.html>`_ pattern together with its
companion `Identity Map <https://martinfowler.com/eaaCatalog/identityMap.html>`_: every
managed file is loaded once and, on exit, written back only if it changed. Each check
reports its modifications either by mutating one of the managed containers (whose own
changelog is collected here) or by appending to :attr:`Session.changelog` directly.

Resources are discovered lazily through :meth:`Session.get`; adding another file type
therefore requires implementing
:class:`~compwa_policy.utilities.resource.ModifiableResource`, without modifying
:class:`Session`.
"""

from __future__ import annotations

import sys
from contextlib import AbstractContextManager
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePixi, ModifiablePyproject
from compwa_policy.utilities.resource import (
    Changelog,
    ModifiablePath,
    ModifiableResource,
)

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Hashable
    from types import TracebackType


R = TypeVar("R", bound=ModifiableResource)


class Session(AbstractContextManager):
    """Shared, mutable working-tree state for all check hooks.

    Load the managed files with :meth:`load` (or pass them in directly, e.g. in tests)
    and use the session as a context manager so that changed files are dumped once on
    exit.
    """

    def __init__(
        self,
        precommit: ModifiablePrecommit | None = None,
        pyproject: ModifiablePyproject | None = None,
    ) -> None:
        self._loaded: dict[tuple[Hashable, ...], ModifiableResource] = {}
        if precommit is not None:
            key = (type(precommit),)
            self._loaded[key] = precommit
        if pyproject is not None:
            key = (type(pyproject),)
            self._loaded[key] = pyproject
        self._entered: set[tuple[Hashable, ...]] = set()
        self._flushed: set[tuple[Hashable, ...]] = set()
        self._is_in_context = False
        self.changelog: Changelog = []
        """Change messages that do not belong to one of the managed containers."""

    @classmethod
    def load(cls, precommit: ModifiablePrecommit | None = None) -> Session:
        """Create a lazy session, optionally with an injected pre-commit resource."""
        return cls(precommit=precommit)

    def get(self, resource: type[R]) -> R:
        """Return the one session-owned instance of *resource*, loading it lazily."""
        key = (resource,)
        loaded = self._loaded.get(key)
        if loaded is None:
            loaded = resource.load()
            self._loaded[key] = loaded
        if self._is_in_context and key not in self._entered:
            loaded.__enter__()  # noqa: PLC2801
            self._entered.add(key)
        return cast("R", loaded)

    def get_path(self, path: Path | str) -> ModifiablePath:
        """Return the session-owned generic resource for one working-tree path."""
        normalized = Path(path)
        key = (ModifiablePath, normalized)
        loaded = self._loaded.get(key)
        if loaded is None:
            loaded = ModifiablePath.load_path(normalized)
            self._loaded[key] = loaded
        if self._is_in_context and key not in self._entered:
            loaded.__enter__()  # noqa: PLC2801
            self._entered.add(key)
        return cast("ModifiablePath", loaded)

    @property
    def precommit(self) -> ModifiablePrecommit:
        """The managed :code:`.pre-commit-config.yaml` file."""
        if (
            not CONFIG_PATH.precommit.exists()
            and (ModifiablePrecommit,) not in self._loaded
        ):
            msg = "This session has no .pre-commit-config.yaml loaded"
            raise ValueError(msg)
        return self.get(ModifiablePrecommit)

    @property
    def pyproject(self) -> ModifiablePyproject | None:
        """The managed :code:`pyproject.toml` file, if the repository has one."""
        if (
            not CONFIG_PATH.pyproject.exists()
            and (ModifiablePyproject,) not in self._loaded
        ):
            return None
        return self.get(ModifiablePyproject)

    @property
    def pixi(self) -> ModifiablePixi:
        """The managed :code:`pixi.toml` file."""
        return self.get(ModifiablePixi)

    def collect_changes(self) -> Changelog:
        """Aggregate every reported change.

        Call this *inside* the context (before the files are dumped on exit). The order
        mirrors the historical flat dispatch: free-form messages first (in the order the
        checks ran), then the container changelogs.
        """
        messages: Changelog = list(self.changelog)
        for resource in self._loaded.values():
            messages += resource.changelog
        return messages

    def flush(self) -> Changelog:
        """Write each changed resource at most once and return the run changelog."""
        messages = self.collect_changes()
        for resource_type, resource in self._loaded.items():
            if resource_type not in self._flushed and resource.changed:
                resource.dump()
                self._flushed.add(resource_type)
        return messages

    def __enter__(self) -> Self:
        self._is_in_context = True
        for resource_type, resource in self._loaded.items():
            resource.__enter__()
            self._entered.add(resource_type)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        try:
            if exc_type is None:
                self.flush()
        finally:
            self._is_in_context = False
        return False
