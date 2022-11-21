# pylint: disable=no-name-in-module
"""Helper functions for modifying :file:`.pre-commit.config.yaml`."""

import os.path
import re
from pathlib import Path
from typing import Any, List, Optional, Tuple, Type, TypeVar, Union

import attrs
import yaml
from attrs import define
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


@define
class PrecommitCi:
    """https://pre-commit.ci/#configuration."""

    autofix_commit_msg: str = "[pre-commit.ci] auto fixes [...]"
    autofix_prs: bool = True
    autoupdate_commit_msg: str = "[pre-commit.ci] pre-commit autoupdate"
    autoupdate_schedule: str = "weekly"
    skip: Optional[List[str]] = None
    submodules: bool = False


@define
class Hook:
    """https://pre-commit.com/#pre-commit-configyaml---hooks."""

    id: str  # noqa: A003
    name: Optional[str] = None
    description: Optional[str] = None
    entry: Optional[str] = None
    alias: Optional[str] = None
    additional_dependencies: List[str] = []
    args: List[str] = []
    files: Optional[str] = None
    exclude: Optional[str] = None
    types: Optional[List[str]] = None
    require_serial: bool = False
    language: Optional[str] = None
    always_run: Optional[bool] = None
    pass_filenames: Optional[bool] = None


@define
class Repo:
    """https://pre-commit.com/#pre-commit-configyaml---repos."""

    repo: str
    hooks: List[Hook]
    rev: Optional[str] = None

    def get_hook_index(self, hook_id: str) -> Optional[int]:
        for i, hook in enumerate(self.hooks):
            if hook.id == hook_id:
                return i
        return None


@define
class PrecommitConfig:
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
        return fromdict(definition, PrecommitConfig)

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


_T = TypeVar("_T", Hook, PrecommitCi, PrecommitConfig, Repo)


def asdict(inst: Any) -> dict:
    return attrs.asdict(
        inst,
        recurse=True,
        filter=lambda a, v: a.init and a.default != v,
    )


def fromdict(definition: dict, typ: Type[_T]) -> _T:
    if typ in {Hook, PrecommitCi}:
        return typ(**definition)  # type: ignore[return-value]
    if typ is Repo:
        definition = {
            **definition,
            "hooks": [fromdict(i, Hook) for i in definition["hooks"]],
        }
        return Repo(**definition)  # type: ignore[return-value]
    if typ is PrecommitConfig:
        definition = {
            **definition,
            "repos": [fromdict(i, Repo) for i in definition["repos"]],
        }
        if "ci" in definition:
            definition["ci"] = fromdict(definition["ci"], PrecommitCi)
        return PrecommitConfig(**definition)  # type: ignore[return-value]
    raise NotImplementedError(f"No implementation for type {typ.__name__}")
