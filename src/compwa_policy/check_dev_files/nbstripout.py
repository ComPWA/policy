"""Check the nbstripout hook in the pre-commit config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruamel.yaml.scalarstring import LiteralScalarString

from compwa_policy.utilities.precommit.struct import Hook, Repo

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit


def main(precommit: ModifiablePrecommit, slideshow: bool) -> None:
    repo_url = "https://github.com/kynan/nbstripout"
    repo = precommit.find_repo(repo_url)
    if repo is None:
        return
    extra_keys_argument = {
        "cell.attachments",
        "cell.metadata.code_folding",
        "cell.metadata.editable",
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
    }
    if not slideshow:
        extra_keys_argument.add("cell.metadata.slideshow")
    existing_hooks = repo["hooks"]
    if existing_hooks:
        args = existing_hooks[0].get("args", [])
        if len(args) >= 2:  # noqa: PLR2004
            existing_keys = {line.strip() for line in args[1].split("\n")}
            existing_keys = {key for key in existing_keys if key}
            extra_keys_argument.update(existing_keys)
    expected_repo = Repo(
        repo=repo_url,
        rev="",
        hooks=[
            Hook(
                id="nbstripout",
                args=[
                    "--extra-keys",
                    LiteralScalarString("\n".join(sorted(extra_keys_argument)) + "\n"),
                ],
            )
        ],
    )
    precommit.update_single_hook_repo(expected_repo)
