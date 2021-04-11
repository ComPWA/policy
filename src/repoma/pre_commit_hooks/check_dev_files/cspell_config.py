"""Check the configuration for cspell.

See `cSpell
<https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell>`_.
"""

import os

from repoma.pre_commit_hooks.errors import PrecommitError


def check_cspell_config(fix: bool) -> None:
    _check_has_config()
    _fix_config_name(fix)


def _check_has_config() -> None:
    if not os.path.exists(".cspell.json") and not os.path.exists(
        "cspell.json"
    ):
        raise PrecommitError(
            "This repository contains no .cspell.json config file"
        )


def _fix_config_name(fix: bool) -> None:
    if os.path.exists("cspell.json"):
        if fix:
            os.rename("cspell.json", ".cspell.json")
        raise PrecommitError(
            'Config file for cSpell should be named ".cspell.json"'
        )
