"""Check the nbstripout hook in the pre-commit config."""

from ruamel.yaml.scalarstring import LiteralScalarString

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    find_repo,
    load_precommit_config,
    update_single_hook_precommit_repo,
)


def main() -> None:
    # cspell:ignore nbconvert showmarkdowntxt
    if not CONFIG_PATH.precommit.exists():
        return
    config = load_precommit_config()
    repo_url = "https://github.com/kynan/nbstripout"
    if find_repo(config, repo_url) is None:
        return
    extra_keys_argument = [
        "cell.attachments",
        "cell.metadata.code_folding",
        "cell.metadata.id",
        "cell.metadata.pycharm",
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
    expected_repo = Repo(
        repo=repo_url,
        rev="",
        hooks=[
            Hook(
                id="nbstripout",
                args=[
                    "--extra-keys",
                    LiteralScalarString("\n".join(extra_keys_argument) + "\n"),
                ],
            )
        ],
    )
    update_single_hook_precommit_repo(expected_repo)
