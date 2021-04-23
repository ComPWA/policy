"""Check existing issue and PR templates for GitHub."""

import os

from repoma.pre_commit_hooks.errors import PrecommitError

from ._helpers import REPOMA_DIR

__PR_TEMPLATE_PATH = ".github/pull_request_template.md"
with open(f"{REPOMA_DIR}/{__PR_TEMPLATE_PATH}") as __STREAM:
    __PR_TEMPLATE_CONTENT = __STREAM.read()


def check_github_templates() -> None:
    _check_pr_template()


def _check_pr_template() -> None:
    if not os.path.exists(__PR_TEMPLATE_PATH):
        __write_pr_template()
        raise PrecommitError(
            f'This repository has no "{__PR_TEMPLATE_PATH}" file.'
            " Problem has been fixed."
        )
    with open(__PR_TEMPLATE_PATH) as stream:
        template_content = stream.read()
    if template_content != __PR_TEMPLATE_CONTENT:
        __write_pr_template()
        raise PrecommitError(
            f'PR template "{__PR_TEMPLATE_PATH}" does not contain expected content.'
            " Problem has been fixed."
        )


def __write_pr_template() -> None:
    with open(__PR_TEMPLATE_PATH, "w") as stream:
        stream.write(__PR_TEMPLATE_CONTENT)
