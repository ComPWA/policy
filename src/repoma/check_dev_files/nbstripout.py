"""Check the nbstripout hook in the pre-commit config."""

from typing import Optional

from ruamel.yaml.scalarstring import LiteralScalarString

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.precommit import PrecommitConfig, Repo
from repoma.utilities.yaml import create_prettier_round_trip_yaml

# cspell:ignore nbconvert showmarkdowntxt
__REPO_URL = "https://github.com/kynan/nbstripout"
__HOOK_ID = "nbstripout"
__EXTRA_KEYS_ARGUMENT = [
    "cell.metadata.code_folding",
    "cell.metadata.id",
    "metadata.celltoolbar",
    "metadata.colab.name",
    "metadata.colab.provenance",
    "metadata.interpreter",
    "metadata.notify_time",
    "metadata.toc",
    "metadata.toc-autonumbering",
    "metadata.toc-showcode",
    "metadata.toc-showmarkdowntxt",
    "metadata.toc-showtags",
    "metadata.varInspector",
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
    config = yaml.load(CONFIG_PATH.precommit)
    config["repos"][index]["hooks"][0]["args"] = expected_args
    yaml.dump(config, CONFIG_PATH.precommit)
