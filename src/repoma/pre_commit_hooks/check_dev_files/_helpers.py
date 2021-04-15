import os.path

from repoma.pre_commit_hooks.errors import PrecommitError


def check_has_file(path: str) -> None:
    if not os.path.exists(path) and not os.path.exists("cspell.json"):
        raise PrecommitError(f"This repository contains no {path} config file")
