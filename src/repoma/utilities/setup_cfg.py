"""Helper functions for reading from and writing to :file:`setup.cfg`."""

from configparser import ConfigParser
from typing import List

from repoma.errors import PrecommitError

from . import CONFIG_PATH
from .cfg import open_config


def get_pypi_name() -> str:
    """Extract package name for PyPI from `setup.cfg`.

    >>> get_pypi_name()
    'repo-maintenance'
    """
    cfg = open_setup_cfg()
    if not cfg.has_option("metadata", "name"):
        msg = f"No package name defined in {CONFIG_PATH.setup_cfg}"
        raise PrecommitError(msg)
    return cfg.get("metadata", "name")


def get_supported_python_versions() -> List[str]:
    """Extract supported Python versions from package classifiers.

    >>> get_supported_python_versions()
    ['3.6', '3.7', '3.8', '3.9', '3.10', '3.11']
    """
    cfg = open_setup_cfg()
    if not cfg.has_option("metadata", "classifiers"):
        msg = (
            "This package does not have Python version classifiers. See"
            " https://pypi.org/classifiers."
        )
        raise PrecommitError(msg)
    raw = cfg.get("metadata", "classifiers")
    lines = [s.strip() for s in raw.split("\n")]
    identifier = "Programming Language :: Python :: 3."
    classifiers = list(filter(lambda s: s.startswith(identifier), lines))
    if not classifiers:
        msg = f'setup.cfg does not have any classifiers of the form "{identifier}*"'
        raise PrecommitError(msg)
    prefix = identifier[:-2]
    return [s.replace(prefix, "") for s in classifiers]


def get_repo_url() -> str:
    cfg = open_setup_cfg()
    if not cfg.has_section("metadata"):
        msg = "setup.cfg does not contain a metadata section"
        raise PrecommitError(msg)
    project_urls_def = cfg["metadata"].get("project_urls", None)
    if project_urls_def is None:
        error_message = (
            "Section metadata in setup.cfg does not contain project_urls."
            " Should be something like:\n\n"
            "[metadata]\n"
            "...\n"
            "project_urls =\n"
            "    Tracker = https://github.com/ComPWA/ampform/issues\n"
            "    Source = https://github.com/ComPWA/ampform\n"
            "    ...\n"
        )
        raise PrecommitError(error_message)
    project_url_lines = project_urls_def.split("\n")
    project_url_lines = list(filter(lambda line: line.strip(), project_url_lines))
    project_urls = {}
    for line in project_url_lines:
        url_type, url, *_ = tuple(line.split("="))
        url_type = url_type.strip()
        url = url.strip()
        project_urls[url_type] = url
    source_url = project_urls.get("Source")
    if source_url is None:
        msg = 'metadata.project_urls in setup.cfg does not contain "Source" URL'
        raise PrecommitError(msg)
    return source_url


def open_setup_cfg() -> ConfigParser:
    if not CONFIG_PATH.setup_cfg.exists():
        msg = "This repository contains no setup.cfg file"
        raise PrecommitError(msg)
    return open_config(CONFIG_PATH.setup_cfg)
