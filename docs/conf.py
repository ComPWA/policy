from __future__ import annotations

from sphinx_api_relink.helpers import get_package_version

ORGANIZATION = "ComPWA"
REPO_NAME = "policy"
REPO_TITLE = "ComPWA repository policy"
PACKAGE_NAME = "compwa_policy"

api_github_repo = f"{ORGANIZATION}/{REPO_NAME}"
api_target_substitutions: dict[str, str | tuple[str, str]] = {
    "Array": "tomlkit.items.Array",
    "ConfigParser": "configparser.ConfigParser",
    "K": "typing.TypeVar",
    "P": "typing.ParamSpec",
    "P.args": ("attr", "typing.ParamSpec.args"),
    "P.kwargs": ("attr", "typing.ParamSpec.kwargs"),
    "Path": "pathlib.Path",
    "PythonVersion": "typing.TypeVar",
    "T": "typing.TypeVar",
    "TOMLDocument": "tomlkit.TOMLDocument",
    "Table": "tomlkit.items.Table",
    "V": "typing.TypeVar",
}
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
    "logo": {"text": "ComPWA policy"},
    "repository_url": f"https://github.com/{ORGANIZATION}/{REPO_NAME}",
    "repository_branch": "main",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "show_navbar_depth": 2,
    "show_toc_level": 2,
}
html_title = REPO_TITLE
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
    ("py:class", "CommentedMap"),
]
nitpick_ignore_regex = [
    ("py:class", r"^.*.[A-Z]$"),
    (r"py:.*", r"ruamel\.yaml\..*"),
]
nitpicky = True
primary_domain = "py"
project = PACKAGE_NAME
release = get_package_version(PACKAGE_NAME)
version = get_package_version(PACKAGE_NAME)
