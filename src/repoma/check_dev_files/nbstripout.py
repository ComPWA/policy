"""Check the nbstripout hook in the pre-commit config."""


from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, LiteralScalarString

from repoma.utilities import CONFIG_PATH
from repoma.utilities.precommit import (
    find_repo,
    load_round_trip_precommit_config,
    update_single_hook_precommit_repo,
)


def main() -> None:
    # cspell:ignore nbconvert showmarkdowntxt
    if not CONFIG_PATH.precommit.exists():
        return
    config, _ = load_round_trip_precommit_config()
    repo_url = "https://github.com/kynan/nbstripout"
    idx_and_repo = find_repo(config, repo_url)
    if idx_and_repo is None:
        return
    extra_keys_argument = [
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
    expected_hook = CommentedMap(
        repo=repo_url,
        rev=DoubleQuotedScalarString(""),
        hooks=[
            CommentedMap(
                id="nbstripout",
                args=[
                    "--extra-keys",
                    LiteralScalarString("\n".join(extra_keys_argument) + "\n"),
                ],
            )
        ],
    )
    update_single_hook_precommit_repo(expected_hook)
