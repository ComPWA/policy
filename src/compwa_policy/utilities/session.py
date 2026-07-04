"""In-memory view of the files that :program:`check-dev-files` inspects and modifies.

The `Session` follows the `Unit of Work
<https://martinfowler.com/eaaCatalog/unitOfWork.html>`_ pattern together with its
companion `Identity Map <https://martinfowler.com/eaaCatalog/identityMap.html>`_: every
managed file is loaded once and, on exit, written back only if it changed. Each check
reports its modifications either by mutating one of the managed containers (whose own
changelog is collected here) or by appending to :attr:`Session.changelog` directly.

.. note::

    The two follow-up issues on this design extend this class *additively*: opening the
    session to more file containers (:code:`README.md`, :code:`.vscode/*`, ...) and
    dispatching the check hooks over the session. The public interface used by the
    checks (:attr:`~.Session.precommit`, :attr:`~.Session.pyproject`,
    :attr:`~.Session.changelog`) is intended to stay stable across both.
"""

from __future__ import annotations

import sys
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, TypeAlias

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import ModifiablePyproject

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from types import TracebackType


ChangelogItem: TypeAlias = str
"""A user-facing message that describes one policy change."""

Changelog: TypeAlias = list[ChangelogItem]
"""Messages reported by a policy check."""


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
        self._precommit = precommit
        self._pyproject = pyproject
        self.changelog: Changelog = []
        """Change messages that do not belong to one of the managed containers."""

    @classmethod
    def load(cls, precommit: ModifiablePrecommit | None = None) -> Self:
        """Load every managed file that is present in the working directory.

        An already-loaded *precommit* can be injected (the remaining files are still
        read from disk); otherwise it is loaded from the working directory as well.
        """
        if precommit is None and CONFIG_PATH.precommit.exists():
            precommit = ModifiablePrecommit.load()
        pyproject = (
            ModifiablePyproject.load() if CONFIG_PATH.pyproject.exists() else None
        )
        return cls(precommit, pyproject)

    @property
    def precommit(self) -> ModifiablePrecommit:
        """The managed :code:`.pre-commit-config.yaml` file."""
        if self._precommit is None:
            msg = "This session has no .pre-commit-config.yaml loaded"
            raise ValueError(msg)
        return self._precommit

    @property
    def pyproject(self) -> ModifiablePyproject | None:
        """The managed :code:`pyproject.toml` file, if the repository has one."""
        return self._pyproject

    def collect_changes(self) -> Changelog:
        """Aggregate every reported change.

        Call this *inside* the context (before the files are dumped on exit). The order
        mirrors the historical flat dispatch: free-form messages first (in the order the
        checks ran), then the container changelogs.
        """
        messages: Changelog = list(self.changelog)
        if self._precommit is not None:
            messages += self._precommit.changelog
        if self._pyproject is not None:
            messages += self._pyproject.changelog
        return messages

    def __enter__(self) -> Self:
        if self._precommit is not None:
            self._precommit.__enter__()
        if self._pyproject is not None:
            self._pyproject.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if self._pyproject is not None:
            self._pyproject.__exit__(exc_type, exc_value, tb)
        if self._precommit is not None:
            self._precommit.__exit__(exc_type, exc_value, tb)
        return False
