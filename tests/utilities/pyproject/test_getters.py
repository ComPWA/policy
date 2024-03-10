import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.pyproject.getters import (
    get_package_name,
    get_project_urls,
    get_source_url,
    get_sub_table,
    get_supported_python_versions,
    has_sub_table,
    load_pyproject_toml,
)


def test_get_package_name():
    src = load_pyproject_toml("""
        [project]
        name = "my-package"
    """)
    package_name = get_package_name(src)
    assert package_name == "my-package"


def test_get_package_name_missing():
    src = load_pyproject_toml("""
        [server]
        ip = "192.168.1.1"
        port = 8000

        [server.http]
        enable = true
        port = 8080

        [[users]]
        name = "Alice"
        [[users]]
        name = "Bob"
    """)
    package_name = get_package_name(src)
    assert package_name is None
    with pytest.raises(PrecommitError):
        package_name = get_package_name(src, raise_on_missing=True)


def test_get_project_urls():
    pyproject = load_pyproject_toml("""
        [project]
        name = "my-package"

        [project.urls]
        Documentation = "https://ampform.rtfd.io"
        Source = "https://github.com/ComPWA/ampform"
    """)
    assert get_project_urls(pyproject) == {
        "Documentation": "https://ampform.rtfd.io",
        "Source": "https://github.com/ComPWA/ampform",
    }

    repo_url = get_source_url(pyproject)
    assert repo_url == "https://github.com/ComPWA/ampform"


def test_get_project_urls_missing():
    pyproject = load_pyproject_toml("""
        [project]
        name = "my-package"
    """)
    with pytest.raises(
        PrecommitError,
        match=r"pyproject\.toml does not contain project URLs",
    ):
        get_project_urls(pyproject)


def test_get_source_url_missing():
    pyproject = load_pyproject_toml("""
        [project.urls]
        Documentation = "https://ampform.rtfd.io"
    """)
    with pytest.raises(
        PrecommitError,
        match=r'\[project\.urls\] in pyproject\.toml does not contain a "Source" URL',
    ):
        get_source_url(pyproject)


def test_get_supported_python_versions():
    pyproject = load_pyproject_toml("""
        [project]
        name = "my-package"
        classifiers = [
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
        ]
    """)
    python_versions = get_supported_python_versions(pyproject)
    assert python_versions == ["3.7", "3.8", "3.9"]


def test_get_sub_table():
    document = load_pyproject_toml("""
        [project]
        name = "my-package"

        [project.urls]
        homepage = "https://github.com"
    """)

    sub_table = get_sub_table(document, "project")
    assert sub_table == document["project"]

    urls = get_sub_table(document, "project.urls")
    assert urls["homepage"] == "https://github.com"

    homepage = get_sub_table(document, "project.urls.homepage")
    assert homepage == "https://github.com"

    with pytest.raises(KeyError, match=r"TOML data does not contain 'server.http'"):
        sub_table = get_sub_table(document, "server.http")
    with pytest.raises(KeyError, match=r"TOML data does not contain 'non-existent'"):
        sub_table = get_sub_table(document, "non-existent")


def test_has_sub_table():
    document = load_pyproject_toml("""
        [project]
        name = "my-package"

        [project.urls]
        homepage = "https://github.com"
    """)
    assert has_sub_table(document, "project")
    assert has_sub_table(document, "project.urls")
    assert not has_sub_table(document, "tool")
    assert not has_sub_table(document, "tool.poetry")
