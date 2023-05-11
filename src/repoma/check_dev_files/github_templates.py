"""Check existing issue and PR templates for GitHub."""

import os
import shutil
from pathlib import Path
from typing import List

from repoma.errors import PrecommitError
from repoma.utilities import REPOMA_DIR
from repoma.utilities.executor import Executor

__PR_TEMPLATE_PATH = Path(".github/pull_request_template.md")
__ISSUE_TEMPLATE_PATH = Path(".github/ISSUE_TEMPLATE")


def main() -> None:
    executor = Executor()
    executor(_check_pr_template)
    executor(_check_issue_templates)
    executor.finalize()


def _check_issue_templates() -> None:
    existing_templates = _list_template_files(__ISSUE_TEMPLATE_PATH)
    expected_templates = _list_template_files(REPOMA_DIR / __ISSUE_TEMPLATE_PATH)
    error_message = ""
    if set(existing_templates) != set(expected_templates):
        shutil.rmtree(__ISSUE_TEMPLATE_PATH, ignore_errors=True)
        os.makedirs(__ISSUE_TEMPLATE_PATH, exist_ok=True)
        error_message = f"{__ISSUE_TEMPLATE_PATH} doesn't contain expected templates:\n"
    for basename in expected_templates:
        import_path = REPOMA_DIR / __ISSUE_TEMPLATE_PATH / basename
        export_path = __ISSUE_TEMPLATE_PATH / basename
        expected_content = __get_template_content(import_path)
        existing_content = ""
        if os.path.exists(export_path):
            existing_content = __get_template_content(export_path)
        if expected_content != existing_content:
            if error_message == "":
                error_message = "The following issue  have been updated:\n`"
            error_message += f"  {export_path}\n"
            __write_template(expected_content, export_path)
    if error_message:
        error_message += "Problem has been fixed."
        raise PrecommitError(error_message)


def _check_pr_template() -> None:
    if not os.path.exists(__PR_TEMPLATE_PATH):
        os.makedirs(os.path.dirname(__PR_TEMPLATE_PATH), exist_ok=True)
        expected_content = __get_template_content(REPOMA_DIR / __PR_TEMPLATE_PATH)
        __write_template(expected_content, __PR_TEMPLATE_PATH)
        raise PrecommitError(
            f"This repository has no {__PR_TEMPLATE_PATH} file. Problem has been fixed."
        )
    with open(__PR_TEMPLATE_PATH) as stream:
        template_content = stream.read()
    expected_content = __get_template_content(REPOMA_DIR / __PR_TEMPLATE_PATH)
    if template_content != expected_content:
        __write_template(expected_content, path=__PR_TEMPLATE_PATH)
        raise PrecommitError(
            f"PR template {__PR_TEMPLATE_PATH} does not contain expected"
            " content. Problem has been fixed."
        )


def __get_template_content(path: Path) -> str:
    with open(path) as stream:
        return stream.read()


def _list_template_files(directory: Path) -> List[str]:
    template_files = []
    for _, __, files in os.walk(directory):  # pyright: ignore[reportUnusedVariable]
        template_files.extend(files)
    return template_files


def __write_template(content: str, path: Path) -> None:
    with open(path, "w") as stream:
        stream.write(content)
