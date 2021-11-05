"""Check the nbstripout hook in the pre-commit config."""

from typing import Optional

from ruamel.yaml.scalarstring import LiteralScalarString

from repoma._utilities import (
    CONFIG_PATH,
    find_precommit_hook,
    get_prettier_round_trip_yaml,
)

# cspell:ignore nbconvert showmarkdowntxt
__REPO_URL = "https://github.com/kynan/nbstripout"
__EXTRA_KEYS_ARGUMENT = [
    "cell.metadata.code_folding",
    "metadata.celltoolbar",
    "metadata.interpreter",
    # do not strip metadata.kernelspec for sphinx-book-theme launch buttons
    "metadata.language_info",
    "metadata.notify_time",
    "metadata.toc",
    "metadata.varInspector",
    "metadata.toc-autonumbering",
    "metadata.toc-showcode",
    "metadata.toc-showmarkdowntxt",
    "metadata.toc-showtags",
]


def check_nbstripout() -> None:
    if not _has_nbstripout_hook():
        return
    _update_extra_keys_argument()


def _has_nbstripout_hook() -> bool:
    hook_def = find_precommit_hook(__REPO_URL)
    return hook_def is not None


def _update_extra_keys_argument() -> None:
    """Add an argument to strip additional metadata.

    For more info see https://github.com/kynan/nbstripout#stripping-metadata.
    """
    yaml = get_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.pre_commit)
    index = __find_hook_index(config, __REPO_URL)
    if index is None:
        return
    expected = [
        "--extra-keys",
        LiteralScalarString("\n".join(__EXTRA_KEYS_ARGUMENT) + "\n"),
    ]
    if config["repos"][index]["hooks"][0].get("args") == expected:
        return
    config["repos"][index]["hooks"][0]["args"] = expected
    yaml.dump(config, CONFIG_PATH.pre_commit)


def __find_hook_index(config: dict, repo_url: str) -> Optional[int]:
    repos: list = config["repos"]
    for i, repo in enumerate(repos):
        if repo.get("repo") == repo_url:
            return i
    return None
