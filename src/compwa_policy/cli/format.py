"""``policy format`` — Prettier, TOML, cSpell, EditorConfig, pre-commit."""

from __future__ import annotations

from compwa_policy.cli import _checks
from compwa_policy.cli._options import (
    Disable,
    TombiErrorsOnWarnings,
    TomlFormatterOption,
    build_arguments,
)


def format_(
    tombi_errors_on_warnings: TombiErrorsOnWarnings = None,
    toml_formatter: TomlFormatterOption = None,
    disable: Disable = None,
) -> None:
    """Standardize formatters and linters: Prettier, TOML, cSpell, EditorConfig, pre-commit."""
    args = build_arguments(
        disable=disable,
        tombi_errors_on_warnings=tombi_errors_on_warnings,
        toml_formatter=toml_formatter,
    )
    _checks.dispatch(args, "format")
