"""Remove deprecated linters and formatters."""

from repoma.utilities import remove_configs, remove_from_gitignore
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import remove_precommit_hook
from repoma.utilities.vscode import remove_extension_recommendation


def remove_deprecated_tools(keep_issue_templates: bool) -> None:
    executor = Executor()
    if not keep_issue_templates:
        executor(_remove_github_issue_templates)
    executor(_remove_markdownlint)
    executor.finalize()


def _remove_github_issue_templates() -> None:
    remove_configs(
        [
            ".github/ISSUE_TEMPLATE",
            ".github/pull_request_template.md",
        ]
    )


def _remove_markdownlint() -> None:
    executor = Executor()
    executor(remove_configs, [".markdownlint.json", ".markdownlint.yaml"])
    executor(remove_from_gitignore, ".markdownlint.json")
    executor(
        remove_extension_recommendation,
        # cspell:ignore davidanson markdownlint
        extension_name="davidanson.vscode-markdownlint",
        unwanted=True,
    )
    executor(remove_precommit_hook, "markdownlint")
    executor.finalize()
