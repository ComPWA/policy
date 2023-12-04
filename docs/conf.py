"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full list see the
documentation: https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

from sphinx_api_relink.helpers import get_package_version

REPO_NAME = "repo-maintenance"
PACKAGE_NAME = "repoma"

author = "Common Partial Wave Analysis"
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autosectionlabel_prefix_document = True
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
    "sphinx_api_relink",
    "sphinx_copybutton",
    "sphinxarg.ext",
]
generate_apidoc_package_path = f"../src/{PACKAGE_NAME}"
html_copy_source = True  # needed for download notebook button
html_favicon = "_static/favicon.ico"
html_last_updated_fmt = "%-d %B %Y"
html_logo = (
    "https://raw.githubusercontent.com/ComPWA/ComPWA/04e5199/doc/images/logo.svg"
)
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
    ("py:class", "tomlkit.container.Container"),
]
nitpick_ignore_regex = [
    ("py:class", r"^.*.[A-Z]$"),
    (r"py:.*", r"ruamel\.yaml\..*"),
]
nitpicky = True
primary_domain = "py"
project = REPO_NAME
release = get_package_version(REPO_NAME)
version = get_package_version(REPO_NAME)
