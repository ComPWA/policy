"""Check the nbstripout hook in the pre-commit config."""

from ruamel.yaml.scalarstring import LiteralScalarString

from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.precommit.struct import Hook, Repo


def main(precommit: ModifiablePrecommit) -> None:
    repo_url = "https://github.com/kynan/nbstripout"
    if precommit.find_repo(repo_url) is None:
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
        "metadata.toc-showmarkdowntxt",  # cspell:ignore showmarkdowntxt
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
    precommit.update_single_hook_repo(expected_repo)
