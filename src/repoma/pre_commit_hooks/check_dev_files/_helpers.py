from os.path import dirname, exists

import repoma
from repoma.pre_commit_hooks.errors import PrecommitError

REPOMA_DIR = dirname(repoma.__file__)


def check_has_file(path: str) -> None:
    if not exists(path) and not exists("cspell.json"):
        raise PrecommitError(f"This repository contains no {path} config file")
