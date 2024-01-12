from compwa_policy.check_dev_files.gitpod import (
    _extract_extensions,
    _generate_gitpod_config,
)


def test_get_gitpod_content():
    gitpod_content = _generate_gitpod_config("3.8")
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
    assert gitpod_content["tasks"] == [
        {"init": "pyenv local 3.8"},
        {"init": "pip install -e .[dev]"},
    ]
    assert gitpod_content["vscode"]["extensions"] == _extract_extensions()
