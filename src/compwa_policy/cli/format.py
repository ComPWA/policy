"""``policy format`` — Prettier, TOML, cSpell, EditorConfig, pre-commit."""

from __future__ import annotations

from compwa_policy.cli import _checks
from compwa_policy.cli._options import (
    NoCspellUpdate,
    TombiErrorsOnWarnings,
    TomlFormatterOption,
    build_arguments,
)


def format_(
    no_cspell_update: NoCspellUpdate = None,
    tombi_errors_on_warnings: TombiErrorsOnWarnings = None,
    toml_formatter: TomlFormatterOption = None,
) -> None:
    """Standardize formatters and linters: Prettier, TOML, cSpell, EditorConfig, pre-commit."""
    args = build_arguments(
        no_cspell_update=no_cspell_update,
        tombi_errors_on_warnings=tombi_errors_on_warnings,
        toml_formatter=toml_formatter,
    )
    _checks.dispatch(args, "format")
