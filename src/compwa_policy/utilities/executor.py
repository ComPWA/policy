"""Collect `.PrecommitError` instances from several executed functions."""

from __future__ import annotations

import sys
import time
from typing import Callable, TypeVar

import attr

from compwa_policy.errors import PrecommitError

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


@attr.s(on_setattr=attr.setters.frozen)
class Executor:
    """Execute functions and collect any `.PrecommitError` exceptions.

    .. automethod:: __call__
    """

    error_messages: list[str] = attr.ib(factory=list, init=False)

    def __call__(
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T | None:
        """Execute a function and collect any `.PrecommitError` exceptions."""
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
            self.error_messages.append(error_message)
            return None
        else:
            return result

    def finalize(self, exception: bool = True) -> int:
        error_msg = self.merge_messages()
        if error_msg:
            if exception:
                raise PrecommitError(error_msg)
            print(error_msg)  # noqa: T201
            return 1
        return 0

    def merge_messages(self) -> str:
        stripped_messages = (s.strip() for s in self.error_messages)
        return "\n--------------------\n".join(stripped_messages)
