from compwa_policy.repo.gitpod import _extract_extensions, _generate_gitpod_config
from compwa_policy.utilities.session import Session


def describe_generate_gitpod_config():
    def builds_expected_sections():
        with Session() as session:
            gitpod_content = _generate_gitpod_config(session, "3.8")
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
        with Session() as session:
            assert gitpod_content["vscode"]["extensions"] == _extract_extensions(
                session
            )
