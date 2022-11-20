# pylint: disable=no-name-in-module
"""Helper functions for modifying :file:`.pre-commit.config.yaml`."""

import os.path
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel
from ruamel.yaml import YAML

from repoma.errors import PrecommitError

from . import CONFIG_PATH
from .yaml import create_prettier_round_trip_yaml


def load_round_trip_precommit_config(
    path: Path = CONFIG_PATH.precommit,
) -> Tuple[dict, YAML]:
    yaml_parser = create_prettier_round_trip_yaml()
    config = yaml_parser.load(path)
    return config, yaml_parser


class PrecommitCi(BaseModel):
    """https://pre-commit.ci/#configuration."""

    autofix_commit_msg: str = "[pre-commit.ci] auto fixes [...]"
    autofix_prs: bool = True
    autoupdate_commit_msg: str = "[pre-commit.ci] pre-commit autoupdate"
    autoupdate_schedule: str = "weekly"
    skip: List[str] = []
    submodules: bool = False


class Hook(BaseModel):
    """https://pre-commit.com/#pre-commit-configyaml---hooks."""

    id: str  # noqa: A003
    name: Optional[str] = None
    entry: Optional[str] = None  # noqa: A003
    alias: Optional[str] = None
    additional_dependencies: List[str] = []
    args: List[str] = []
    files: Optional[str] = None
    exclude: Optional[str] = None
    types: Optional[List[str]] = None
    language: Optional[str] = None
    always_run: Optional[bool] = None
    pass_filenames: Optional[bool] = None


class Repo(BaseModel):
    """https://pre-commit.com/#pre-commit-configyaml---repos."""

    repo: str
    rev: Optional[str] = None
    hooks: List[Hook]

    def get_hook_index(self, hook_id: str) -> Optional[int]:
        for i, hook in enumerate(self.hooks):
            if hook.id == hook_id:
                return i
        return None


class PrecommitConfig(BaseModel):
    """https://pre-commit.com/#pre-commit-configyaml---top-level."""

    repos: List[Repo]
    ci: Optional[PrecommitCi] = None
    files: str = ""
    exclude: str = "^$"
    fail_fast: bool = False

    @classmethod
    def load(cls, path: Union[Path, str] = CONFIG_PATH.precommit) -> "PrecommitConfig":
        if not os.path.exists(path):
            raise PrecommitError(f"This repository contains no {path}")
        with open(path) as stream:
            definition = yaml.safe_load(stream)
        return PrecommitConfig(**definition)

    def find_repo(self, search_pattern: str) -> Optional[Repo]:
        for repo in self.repos:
            url = repo.repo
            if re.search(search_pattern, url):
                return repo
        return None

    def get_repo_index(self, search_pattern: str) -> Optional[int]:
        for i, repo in enumerate(self.repos):
            url = repo.repo
            if re.search(search_pattern, url):
                return i
        return None
