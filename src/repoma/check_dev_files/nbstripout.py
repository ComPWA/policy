"""Check the nbstripout hook in the pre-commit config."""

from typing import Optional

from ruamel.yaml.scalarstring import LiteralScalarString

from repoma._utilities import (
    CONFIG_PATH,
    PrecommitConfig,
    Repo,
    create_prettier_round_trip_yaml,
)
from repoma.errors import PrecommitError

# cspell:ignore nbconvert showmarkdowntxt
__REPO_URL = "https://github.com/kynan/nbstripout"
__HOOK_ID = "nbstripout"
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


def main() -> None:
    repo = _get_nbstripout_precommit_repo()
    if repo is None:
        return
    _update_extra_keys_argument(repo)


def _get_nbstripout_precommit_repo() -> Optional[Repo]:
    config = PrecommitConfig.load()
    return config.find_repo(__REPO_URL)


def _update_extra_keys_argument(repo: Repo) -> None:
    """Add an argument to strip additional metadata.

    For more info see https://github.com/kynan/nbstripout#stripping-metadata.
    """
    index = repo.get_hook_index(__HOOK_ID)
    if index is None:
        raise PrecommitError(
            f'The following repo is missing hook ID "{__HOOK_ID}":'
            f" {__REPO_URL}"
        )
    expected_args = [
        "--extra-keys",
        LiteralScalarString("\n".join(__EXTRA_KEYS_ARGUMENT) + "\n"),
    ]
    if repo.hooks[index].args == [str(s) for s in expected_args]:
        return
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.pre_commit)
    config["repos"][index]["hooks"][0]["args"] = expected_args
    yaml.dump(config, CONFIG_PATH.pre_commit)
