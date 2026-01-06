"""Collect `.PrecommitError` instances from several executed functions.

.. autolink-preface::
    from compwa_policy.errors import PrecommitError
    from compwa_policy.utilities.executor import Executor
"""

from __future__ import annotations

import inspect
import operator
import os
import sys
import time
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, TypeVar

from compwa_policy.errors import PrecommitError

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

T = TypeVar("T")
P = ParamSpec("P")


class Executor(AbstractContextManager):
    r"""Execute functions and collect any `.PrecommitError` exceptions.

    The `Executor` is a context manager that can be used to sequentially execute
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
    >>> with Executor(raise_exception=False) as execute:
    ...     execute(function1)
    ...     execute(function2)
    ...     execute(function3)
    Error message 1
    --------------------
    Error message 2

    .. automethod:: __call__
    """

    def __init__(self, raise_exception: bool = True) -> None:
        self.__raise_exception = raise_exception
        self.__error_messages: list[str] = []
        self.__is_in_context = False
        self.__execution_times: dict[str, float] = {}

    @property
    def error_messages(self) -> tuple[str, ...]:
        """View the collected error messages.

        .. note::
            Set :code:`COMPWA_POLICY_DEBUG=1` to enable profiling the execution times.
        """
        return tuple(self.__error_messages)

    def __call__(
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T | None:
        """Execute a function and collect any `.PrecommitError` exceptions."""
        if not self.__is_in_context:
            msg = "The __call__ method can only be used within a context manager."
            raise RuntimeError(msg)
        try:
            if os.getenv("COMPWA_POLICY_DEBUG") != "0":
                start_time = time.time()
                result = function(*args, **kwargs)
                end_time = time.time()
                source_file = inspect.getsourcefile(function)
                line_number = inspect.getsourcelines(function)[1]
                location = f"{source_file}:{line_number}"
                if function_name := getattr(function, "__name__", None):
                    location += f" ({function_name})"
                self.__execution_times[location] = end_time - start_time
            else:
                result = function(*args, **kwargs)
        except PrecommitError as exception:
            error_message = str("\n".join(exception.args))
            self.__error_messages.append(error_message)
            return None
        else:
            return result

    def __enter__(self) -> Self:
        self.__is_in_context = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is not None and not issubclass(exc_type, PrecommitError):
            return False
        if isinstance(exc_value, PrecommitError):
            self.__error_messages.append(str("\n".join(exc_value.args)))
        error_msg = self.merge_messages()
        if error_msg:
            if self.__raise_exception:
                raise PrecommitError(error_msg)
            print(error_msg)  # noqa: T201
        if os.getenv("COMPWA_POLICY_DEBUG") is not None:
            self.print_execution_times()
        return True

    def merge_messages(self) -> str:
        stripped_messages = (s.strip() for s in self.__error_messages)
        return "\n--------------------\n".join(stripped_messages)

    def print_execution_times(self) -> None:
        total_time = sum(self.__execution_times.values())
        if total_time > 0.08:  # noqa: PLR2004
            print(f"\nTotal sub-hook time: {total_time:.2f} s")  # noqa: T201
            sorted_times = sorted(
                self.__execution_times.items(), key=operator.itemgetter(1), reverse=True
            )
            for function_name, sub_time in sorted_times:
                if sub_time < 0.03:  # noqa: PLR2004
                    break
                print(f"{sub_time:>7.2f} s  {function_name}")  # noqa: T201
