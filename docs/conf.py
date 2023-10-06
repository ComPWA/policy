"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full list see the
documentation: https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import contextlib
import os
import shutil
import subprocess
import sys
from typing import Optional

import requests

if sys.version_info < (3, 8):
    from importlib_metadata import version as get_package_version
else:
    from importlib.metadata import version as get_package_version


def fetch_logo(url: str, output_path: str) -> None:
    if os.path.exists(output_path):
        return
    online_content = requests.get(url, allow_redirects=True, timeout=10)
    with open(output_path, "wb") as stream:
        stream.write(online_content.content)


def generate_api(package: str) -> None:
    shutil.rmtree("api", ignore_errors=True)
    subprocess.call(
        " ".join(
            [
                "sphinx-apidoc",
                f"../src/{package}/",
                f"../src/{package}/version.py",
                "-o api/",
                "--force",
                "--no-toc",
                "--templatedir _templates",
                "--separate",
            ]
        ),
        shell=True,  # noqa: S602
    )


def get_html_logo_path() -> Optional[str]:
    logo_path = "_static/logo.svg"
    os.makedirs(os.path.dirname(logo_path), exist_ok=True)
    with contextlib.suppress(requests.exceptions.ConnectionError):
        fetch_logo(
            url="https://raw.githubusercontent.com/ComPWA/ComPWA/04e5199/doc/images/logo.svg",
            output_path=logo_path,
        )
    if os.path.exists(logo_path):
        return logo_path
    return None


def get_version(package_name: str) -> str:
    v = get_package_version(package_name)
    return ".".join(v.split(".")[:3])


REPO_NAME = "repo-maintenance"
PACKAGE_NAME = "repoma"
generate_api(PACKAGE_NAME)

author = "Common Partial Wave Analysis"
autodoc_member_order = "bysource"
autosectionlabel_prefix_document = True
autodoc_typehints_format = "short"
copybutton_prompt_is_regexp = True
copybutton_prompt_text = r">>> |\.\.\. "  # doctest
copyright = "2023, Common Partial Wave Analysis"  # noqa: A001
default_role = "py:obj"
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]
html_copy_source = True  # needed for download notebook button
html_favicon = "_static/favicon.ico"
html_last_updated_fmt = "%-d %B %Y"
html_logo = get_html_logo_path()
html_show_copyright = False
html_show_sourcelink = False
html_show_sphinx = False
html_sourcelink_suffix = ""
html_static_path = ["_static"]
html_theme = "sphinx_book_theme"
html_theme_options = {
    "logo": {"text": REPO_NAME},
    "repository_url": f"https://github.com/ComPWA/{REPO_NAME}",
    "repository_branch": "main",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "show_navbar_depth": 2,
    "show_toc_level": 2,
}
html_title = REPO_NAME
intersphinx_mapping = {
    "attrs": ("https://www.attrs.org/en/stable", None),
    "nbformat": ("https://nbformat.readthedocs.io/en/stable", None),
    "python": ("https://docs.python.org/3", None),
    "tomlkit": ("https://tomlkit.readthedocs.io/en/stable", None),
}
myst_enable_extensions = [
    "colon_fence",
]
nitpick_ignore = [
    ("py:class", "repoma.utilities.precommit.T"),
    ("py:class", "tomlkit.container.Container"),
]
nitpick_ignore_regex = [
    (r"py:.*", r"ruamel\.yaml\..*"),
]
nitpicky = True
primary_domain = "py"
project = REPO_NAME
release = get_version(REPO_NAME)
version = get_version(REPO_NAME)
