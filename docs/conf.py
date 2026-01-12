from __future__ import annotations

from sphinx_api_relink.helpers import get_branch_name, get_package_version

BRANCH = get_branch_name()
ORGANIZATION = "ComPWA"
REPO_NAME = "policy"
REPO_TITLE = "ComPWA repository policy"
PACKAGE_NAME = "compwa_policy"

add_module_names = False
api_github_repo = f"{ORGANIZATION}/{REPO_NAME}"
api_target_substitutions: dict[str, str | tuple[str, str]] = {
    "Array": "tomlkit.items.Array",
    "ConfigParser": "configparser.ConfigParser",
    "Frequency": "typing.Literal",
    "InlineTable": "tomlkit.items.InlineTable",
    "IO": "typing.IO",
    "Iterable": "typing.Iterable",
    "K": "typing.TypeVar",
    "Mapping": "collections.abc.Mapping",
    "NotRequired": ("obj", "typing.NotRequired"),
    "P.args": ("attr", "typing.ParamSpec.args"),
    "P.kwargs": ("attr", "typing.ParamSpec.kwargs"),
    "P": "typing.ParamSpec",
    "PackageManagerChoice": (
        "obj",
        "compwa_policy.check_dev_files.conda.PackageManagerChoice",
    ),
    "Path": "pathlib.Path",
    "ProjectURLs": "list",
    "PyprojectTOML": "dict",
    "PythonVersion": "str",
    "RemovedKeys": ("obj", "compwa_policy.utilities.vscode.RemovedKeys"),
    "Sequence": "typing.Sequence",
    "T": "typing.TypeVar",
    "Table": "tomlkit.items.Table",
    "TOMLDocument": "tomlkit.TOMLDocument",
    "ty.TypeChecker": ("obj", "compwa_policy.check_dev_files.ty.TypeChecker"),
    "TypeChecker": ("obj", "compwa_policy.check_dev_files.ty.TypeChecker"),
    "typing_extensions.NotRequired": ("obj", "typing.NotRequired"),
    "upgrade_lock.Frequency": (
        "obj",
        "compwa_policy.check_dev_files.upgrade_lock.Frequency",
    ),
    "V": "typing.TypeVar",
}
author = "Common Partial Wave Analysis"
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autosectionlabel_prefix_document = True
codeautolink_concat_default = True
copybutton_prompt_is_regexp = True
copybutton_prompt_text = r">>> |\.\.\. "  # doctest
copyright = "2023, Common Partial Wave Analysis"  # noqa: A001
default_role = "py:obj"
extensions = [
    "myst_parser",
    "sphinx_api_relink",
    "sphinx_codeautolink",
    "sphinx_copybutton",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
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
    "icon_links": [
        {
            "name": "Common Partial Wave Analysis",
            "url": "https://compwa.github.io",
            "icon": "_static/favicon.ico",
            "type": "local",
        },
        {
            "name": "GitHub",
            "url": f"https://github.com/{ORGANIZATION}/{REPO_NAME}",
            "icon": "fa-brands fa-github",
        },
    ],
    "logo": {"text": "ComPWA policy"},
    "path_to_docs": "docs",
    "repository_branch": BRANCH,
    "repository_url": f"https://github.com/{ORGANIZATION}/{REPO_NAME}",
    "show_navbar_depth": 2,
    "show_toc_level": 2,
    "use_download_button": False,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
    "use_source_button": True,
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
    ("py:class", "ProjectURLs"),
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
