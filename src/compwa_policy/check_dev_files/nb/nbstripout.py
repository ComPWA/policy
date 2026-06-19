"""Check the nbstripout hook in the pre-commit config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruamel.yaml.scalarstring import LiteralScalarString

from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit.struct import Hook, Repo

if TYPE_CHECKING:
    from compwa_policy.utilities.precommit import ModifiablePrecommit


def main(
    precommit: ModifiablePrecommit,
    has_notebooks: bool,
    allowed_cell_metadata: list[str],
) -> None:
    if not has_notebooks:
        precommit.remove_hook("nbstripout")
    else:
        with Executor() as do:
            do(_update_precommit_hook, precommit, allowed_cell_metadata)
            do(_update_strip_nb_whitespace, precommit)


def _update_precommit_hook(
    precommit: ModifiablePrecommit, allowed_cell_metadata: list[str]
) -> None:
    extra_keys_argument = {
        "cell.attachments",
        "cell.metadata.code_folding",
        "cell.metadata.editable",
        "cell.metadata.id",
        "cell.metadata.pycharm",
        "cell.metadata.slideshow",
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
    extra_keys_argument -= {f"cell.metadata.{key}" for key in allowed_cell_metadata}
    expected_repo = Repo(
        repo="https://github.com/kynan/nbstripout",
        rev="",
        hooks=[
            Hook(
                id="nbstripout",
                args=[
                    "--drop-empty-cells",
                    "--extra-keys",
                    LiteralScalarString("\n".join(sorted(extra_keys_argument)) + "\n"),
                ],
            )
        ],
    )
    precommit.update_single_hook_repo(expected_repo)


def _update_strip_nb_whitespace(precommit: ModifiablePrecommit) -> None:
    precommit.update_hook("ComPWA/policy", Hook(id="strip-nb-whitespace"))
