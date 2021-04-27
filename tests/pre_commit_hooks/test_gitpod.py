import pytest

from repoma.pre_commit_hooks.check_dev_files.gitpod import (
    _extract_extensions,
    _generate_gitpod_config,
)


def test_extract_extensions():
    assert _extract_extensions() == [
        # cspell:disable
        "bungcip.better-toml",
        "christian-kohler.path-intellisense",
        "codestream.codestream",
        "davidanson.vscode-markdownlint",
        "eamodio.gitlens",
        "editorconfig.editorconfig",
        "esbenp.prettier-vscode",
        "github.vscode-pull-request-github",
        "littlefoxteam.vscode-python-test-adapter",
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-vsliveshare.vsliveshare",
        "redhat.vscode-yaml",
        "ryanluker.vscode-coverage-gutters",
        "stkb.rewrap",
        "streetsidesoftware.code-spell-checker",
        "travisillig.vscode-json-stable-stringify",
        "tyriar.sort-lines",
        "yzhang.markdown-all-in-one",
        # cspell:enable
    ]


@pytest.mark.parametrize("pin_dependencies", [False, True])
def test_get_gitpod_content(pin_dependencies: bool):
    gitpod_content = _generate_gitpod_config(pin_dependencies)
    assert set(gitpod_content) == {
        "github",
        "tasks",
        "vscode",
    }
    assert gitpod_content["github"] == {
        "prebuilds": {
            "addBadge": False,
            "addComment": False,
            "addLabel": False,
            "branches": False,
            "master": True,
            "pullRequests": True,
            "pullRequestsFromForks": True,
        }
    }
    if pin_dependencies:
        assert gitpod_content["tasks"] == [
            {"init": "pip install -c .constraints/py3.8.txt -e .[dev]"},
        ]
    else:
        assert gitpod_content["tasks"] == [
            {"init": "pip install -e .[dev]"},
        ]
    assert gitpod_content["vscode"]["extensions"] == _extract_extensions()
