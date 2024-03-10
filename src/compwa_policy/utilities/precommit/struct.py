# noqa: D100
from __future__ import annotations

import sys

if sys.version_info < (3, 8):
    from typing_extensions import Literal, TypedDict
else:
    from typing import Literal, TypedDict
if sys.version_info < (3, 11):
    from typing_extensions import NotRequired
else:
    from typing import NotRequired


class PrecommitConfig(TypedDict):
    """https://pre-commit.com/#pre-commit-configyaml---top-level."""

    ci: NotRequired[PrecommitCi]
    repos: list[Repo]
    default_stages: NotRequired[list[str]]
    files: NotRequired[str]
    exclude: NotRequired[str]
    fail_fast: NotRequired[bool]
    minimum_pre_commit_version: NotRequired[str]


class PrecommitCi(TypedDict):
    """https://pre-commit.ci/#configuration."""

    autofix_commit_msg: NotRequired[str]
    autofix_prs: NotRequired[bool]
    autoupdate_branch: NotRequired[str]
    autoupdate_commit_msg: NotRequired[str]
    autoupdate_schedule: NotRequired[Literal["weekly", "monthly", "quarterly"]]
    skip: NotRequired[list[str]]
    submodules: NotRequired[bool]


class Repo(TypedDict):
    """https://pre-commit.com/#pre-commit-configyaml---repos."""

    repo: str
    rev: str
    hooks: list[Hook]


class Hook(TypedDict):
    """https://pre-commit.com/#pre-commit-configyaml---hooks."""

    id: str
    alias: NotRequired[str]
    name: NotRequired[str]
    language_version: NotRequired[str]
    files: NotRequired[str]
    exclude: NotRequired[str]
    types: NotRequired[list[str]]
    types_or: NotRequired[list[str]]
    exclude_types: NotRequired[list[str]]
    args: NotRequired[list[str]]
    stages: NotRequired[list[str]]
    additional_dependencies: NotRequired[list[str]]
    always_run: NotRequired[bool]
    verbose: NotRequired[bool]
    log_file: NotRequired[str]
    pass_filenames: NotRequired[bool]
