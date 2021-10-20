from repoma._utilities import get_repo_url


def test_get_repo_url():
    assert get_repo_url() == "https://github.com/ComPWA/repo-maintenance"
