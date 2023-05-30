"""Check the nbstripout hook in the pre-commit config."""

from typing import Optional, Tuple

from ruamel.yaml.scalarstring import LiteralScalarString

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.precommit import PrecommitConfig, Repo
from repoma.utilities.yaml import create_prettier_round_trip_yaml

# cspell:ignore nbconvert showmarkdowntxt
__REPO_URL = "https://github.com/kynan/nbstripout"
__HOOK_ID = "nbstripout"
__EXTRA_KEYS_ARGUMENT = [
    "cell.attachments",
    "cell.metadata.code_folding",
    "cell.metadata.id",
    "cell.metadata.user_expressions",
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
    "metadata.vscode",
]


def main() -> None:
    index, repo = _get_nbstripout_precommit_repo()
    if repo is None or index is None:
        return
    _update_extra_keys_argument(index, repo)


def _get_nbstripout_precommit_repo() -> Tuple[Optional[int], Optional[Repo]]:
    config = PrecommitConfig.load()
    repo = config.find_repo(__REPO_URL)
    index = config.get_repo_index(__REPO_URL)
    return index, repo


def _update_extra_keys_argument(repo_index: int, repo: Repo) -> None:
    """Add an argument to strip additional metadata.

    For more info see https://github.com/kynan/nbstripout#stripping-metadata.
    """
    index = repo.get_hook_index(__HOOK_ID)
    if index is None:
        raise PrecommitError(
            f'The following repo is missing hook ID "{__HOOK_ID}": {__REPO_URL}'
        )
    expected_args = [
        "--extra-keys",
        LiteralScalarString("\n".join(__EXTRA_KEYS_ARGUMENT) + "\n"),
    ]
    if repo.hooks[index].args == [str(s) for s in expected_args]:
        return
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(CONFIG_PATH.precommit)
    repos = config["repos"]
    hooks = repos[repo_index]["hooks"][index]
    hooks["args"] = expected_args
    if repo_index != len(repos):
        repos.yaml_set_comment_before_after_key(repo_index + 1, before="\n")
    yaml.dump(config, CONFIG_PATH.precommit)
