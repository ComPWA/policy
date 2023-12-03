"""Helper functions for reading from and writing to :file:`setup.cfg`."""

from __future__ import annotations

import os
import sys
from textwrap import dedent
from typing import TYPE_CHECKING

from attrs import field, frozen

from repoma.errors import PrecommitError
from repoma.utilities.pyproject import get_sub_table, load_pyproject

from . import CONFIG_PATH
from .cfg import open_config

if TYPE_CHECKING:
    from configparser import ConfigParser

    from tomlkit import TOMLDocument

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


PythonVersion = Literal["3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12"]


@frozen
class ProjectInfo:
    name: str | None = None
    supported_python_versions: list[PythonVersion] | None = None
    urls: dict[str, str] = field(factory=dict)

    def is_empty(self) -> bool:
        return (
            self.name is None
            and self.supported_python_versions is None
            and not self.urls
        )

    @staticmethod
    def from_pyproject_toml(pyproject: TOMLDocument) -> ProjectInfo:
        if "project" not in pyproject:
            return ProjectInfo()
        project = get_sub_table(pyproject, "project")
        return ProjectInfo(
            name=project.get("name"),
            supported_python_versions=_extract_python_versions(
                project.get("classifiers", [])
            ),
            urls=project.get("urls", {}),
        )

    @staticmethod
    def from_setup_cfg(cfg: ConfigParser) -> ProjectInfo:
        if not cfg.has_section("metadata"):
            return ProjectInfo()
        metadata = dict(cfg.items("metadata"))
        project_urls_raw: str = metadata.get("project_urls", "\n")
        project_url_lines = project_urls_raw.split("\n")
        project_url_lines = list(filter(lambda line: line.strip(), project_url_lines))
        project_urls = {}
        for line in project_url_lines:
            url_type, url, *_ = tuple(line.split("="))
            url_type = url_type.strip()
            url = url.strip()
            project_urls[url_type] = url
        return ProjectInfo(
            name=metadata.get("name"),
            supported_python_versions=_extract_python_versions(
                metadata.get("classifiers", "").split("\n")
            ),
            urls=project_urls,
        )


def get_project_info(pyproject: TOMLDocument | None = None) -> ProjectInfo:
    if pyproject is not None or os.path.exists(CONFIG_PATH.pyproject):
        if pyproject is None:
            pyproject = load_pyproject()
        project_info = ProjectInfo.from_pyproject_toml(pyproject)
        if not project_info.is_empty():
            return project_info
    if os.path.exists(CONFIG_PATH.setup_cfg):
        cfg = open_config(CONFIG_PATH.setup_cfg)
        project_info = ProjectInfo.from_setup_cfg(cfg)
        if not project_info.is_empty():
            return project_info
    msg = f"No valid {CONFIG_PATH.setup_cfg} or {CONFIG_PATH.pyproject} found"
    raise PrecommitError(msg)


def _extract_python_versions(classifiers: list[str]) -> list[PythonVersion] | None:
    identifier = "Programming Language :: Python :: 3."
    version_classifiers = [s for s in classifiers if s.startswith(identifier)]
    if not version_classifiers:
        return None
    prefix = identifier[:-2]
    return [s.replace(prefix, "") for s in version_classifiers]  # type: ignore[misc]


def get_pypi_name(pyproject: TOMLDocument | None = None) -> str:
    """Extract package name for PyPI from :file:`setup.cfg`.

    >>> get_pypi_name()
    'repo-maintenance'
    """
    project_info = get_project_info(pyproject)
    if project_info.name is None:
        msg = (
            f"No package name defined in {CONFIG_PATH.setup_cfg} or"
            f" {CONFIG_PATH.pyproject}"
        )
        raise PrecommitError(msg)
    return project_info.name


def get_supported_python_versions(
    pyproject: TOMLDocument | None = None,
) -> list[PythonVersion]:
    """Extract supported Python versions from package classifiers.

    >>> get_supported_python_versions()
    ['3.10', '3.11', '3.12', '3.7', '3.8', '3.9']
    """
    project_info = get_project_info(pyproject)
    if project_info.supported_python_versions is None:
        msg = "Could not determine Python version classifiers of this package"
        raise PrecommitError(msg)
    return project_info.supported_python_versions


def get_repo_url(pyproject: TOMLDocument | None = None) -> str:
    project_info = get_project_info(pyproject)
    if not project_info.urls:
        msg = dedent("""
            pyproject.toml or setup.cfg does not contain project URLSs. Should be
            something like:

            [project.urls]"
            Documentation = "https://ampform.rtfd.io"
            Source = "https://github.com/ComPWA/ampform"
            Tracker = "https://github.com/ComPWA/ampform/issues"
        """)
        raise PrecommitError(msg)
    source_url = project_info.urls.get("Source")
    if source_url is None:
        msg = '[project.urls] in pyproject.toml does not contain a "Source" URL'
        raise PrecommitError(msg)
    return source_url


def open_setup_cfg() -> ConfigParser:
    if not CONFIG_PATH.setup_cfg.exists():
        msg = "This repository contains no setup.cfg file"
        raise PrecommitError(msg)
    return open_config(CONFIG_PATH.setup_cfg)
