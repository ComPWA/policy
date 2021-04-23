"""Check existing issue and PR templates for GitHub."""

import textwrap
from os.path import exists

from repoma.pre_commit_hooks.errors import PrecommitError

from ._helpers import REPOMA_DIR

__PR_TEMPLATE_PATH = ".github/pull_request_template.md"
with open(f"{REPOMA_DIR}/{__PR_TEMPLATE_PATH}") as __STREAM:
    __PR_TEMPLATE_CONTENT = __STREAM.read()


def check_github_templates(fix: bool) -> None:
    _check_pr_template(fix)


def _check_pr_template(fix: bool) -> None:
    error_message = ""
    if not exists(__PR_TEMPLATE_PATH):
        error_message = f'This repository has no "{__PR_TEMPLATE_PATH}" file. '
        if fix:
            __write_pr_template()
            error_message += "Problem has been fixed."
        else:
            error_message += (
                "Please create this file with the following content:\n\n"
            )
            error_message += textwrap.indent(
                __PR_TEMPLATE_CONTENT, prefix=2 * " "
            )
    else:
        with open(__PR_TEMPLATE_PATH) as stream:
            template_content = stream.read()
        if template_content != __PR_TEMPLATE_CONTENT:
            error_message = (
                f'PR template "{__PR_TEMPLATE_PATH}"'
                " does not contain expected content. "
            )
            if fix:
                __write_pr_template()
                error_message += "Problem has been fixed."
            else:
                error_message += (
                    "Please replace file content with the following:\n\n"
                )
                error_message += textwrap.indent(
                    __PR_TEMPLATE_CONTENT, prefix=2 * " "
                )
    if error_message:
        raise PrecommitError(error_message)


def __write_pr_template() -> None:
    with open(__PR_TEMPLATE_PATH, "w") as stream:
        stream.write(__PR_TEMPLATE_CONTENT)
