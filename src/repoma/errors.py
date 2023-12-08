"""Exceptions that are caught by a pre-commit hook and printed instead."""


class PrecommitError(RuntimeError):
    pass
