"""Collect `.PrecommitError` instances from several executed functions.

.. autolink-preface::
    from compwa_policy.errors import PrecommitError
    from compwa_policy.utilities.executor import executor
"""

from __future__ import annotations

import sys
import time
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Callable, TypeVar

from compwa_policy.errors import PrecommitError

if TYPE_CHECKING:
    from types import TracebackType

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


class executor(AbstractContextManager):  # noqa: N801
    r"""Execute functions and collect any `.PrecommitError` exceptions.

    The `executor` is a context manager that can be used to sequentially execute
    functions and collect any `.PrecommitError` exceptions they raise. The collected
    exceptions are merged and re-raised as a new `.PrecommitError` when the context
    manager exits.

    To avoid raising the exceptions, set the :code:`raise_exception` argument to
    `False`. The collected exceptions will then be printed to the console instead.

    >>> def function1() -> None:
    ...     raise PrecommitError("Error message 1")
    >>> def function2() -> None:
    ...     raise PrecommitError("Error message 2")
    >>> def function3() -> None: ...
    >>>
    >>> with executor(raise_exception=False) as execute:
    ...     execute(function1)
    ...     execute(function2)
    ...     execute(function3)
    Error message 1
    --------------------
    Error message 2

    .. automethod:: __call__
    """

    def __init__(self, raise_exception: bool = True) -> None:
        self._raise_exception = raise_exception
        self.__error_messages: list[str] = []
        self.__is_in_context = False

    @property
    def error_messages(self) -> tuple[str, ...]:
        """View the collected error messages."""
        return tuple(self.__error_messages)

    def __call__(
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T | None:
        """Execute a function and collect any `.PrecommitError` exceptions."""
        if not self.__is_in_context:
            msg = "The __call__ method can only be used within a context manager."
            raise RuntimeError(msg)
        try:
            start_time = time.time()
            result = function(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            if execution_time > 0.05:  # noqa: PLR2004
                function_name = f"{function.__module__}.{function.__name__}"
                print(f"{execution_time:>7.2f} s  {function_name}")  # noqa: T201
        except PrecommitError as exception:
            error_message = str("\n".join(exception.args))
            self.__error_messages.append(error_message)
            return None
        else:
            return result

    def __enter__(self) -> executor:
        self.__is_in_context = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        error_msg = self.merge_messages()
        if error_msg:
            if self._raise_exception:
                raise PrecommitError(error_msg) from exc_value
            print(error_msg)  # noqa: T201

    def merge_messages(self) -> str:
        stripped_messages = (s.strip() for s in self.__error_messages)
        return "\n--------------------\n".join(stripped_messages)
