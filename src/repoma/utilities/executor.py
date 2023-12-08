"""Collect `.PrecommitError` instances from several executed functions."""

from __future__ import annotations

import sys
from typing import Callable, TypeVar

import attr

from repoma.errors import PrecommitError

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


@attr.s(on_setattr=attr.setters.frozen)
class Executor:
    """Execute functions and collect any `.PrecommitError` exceptions."""

    error_messages: list[str] = attr.ib(factory=list, init=False)

    def __call__(
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T | None:
        try:
            return function(*args, **kwargs)
        except PrecommitError as exception:
            error_message = str("\n".join(exception.args))
        self.error_messages.append(error_message)
        return None

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
