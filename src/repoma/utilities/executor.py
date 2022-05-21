"""Collect `.PrecommitError` instances from several executed functions."""

from typing import Any, Callable, List

import attr

from repoma.errors import PrecommitError


@attr.s(on_setattr=attr.setters.frozen)
class Executor:
    """Execute functions and collect any `.PrecommitError` exceptions."""

    error_messages: List[str] = attr.ib(factory=list, init=False)

    def __call__(self, function: Callable, *args: Any, **kwargs: Any) -> None:
        try:
            function(*args, **kwargs)
        except PrecommitError as exception:
            error_message = str("\n".join(exception.args))
            self.error_messages.append(error_message)

    def merge_messages(self) -> str:
        stripped_messages = (s.strip() for s in self.error_messages)
        return "\n--------------------\n".join(stripped_messages)
