from repoma._utilities import (
    copy_config,
    get_precommit_repos,
    get_repo_url,
    open_setup_cfg,
)


def test_copy_config():
    cfg = open_setup_cfg()
    cfg_copy = copy_config(cfg)
    assert cfg_copy is not cfg
    assert cfg_copy == cfg


def test_get_repo_url():
    assert get_repo_url() == "https://github.com/ComPWA/repo-maintenance"


def test_get_precommit_repos():
    repos = get_precommit_repos()
    repo_names = {repo_def["repo"] for repo_def in repos}
    assert repo_names >= {
        "https://github.com/pre-commit/pre-commit-hooks",
        "https://github.com/psf/black",
        "https://github.com/pycqa/pydocstyle",
        "https://github.com/pycqa/flake8",
    }


def test_open_setup_cfg():
    cfg = open_setup_cfg()
    sections = cfg.sections()
    assert sections == [
        "metadata",
        "options",
        "options.extras_require",
        "options.entry_points",
        "options.packages.find",
        "options.package_data",
    ]
    assert cfg.get("metadata", "name") == "repo-maintenance"
