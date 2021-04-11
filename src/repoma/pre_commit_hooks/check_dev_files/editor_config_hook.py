"""Check existence of pre-commit hook for EditorConfig.

If a repository has an ``.editorconfig`` file, it should have an `EditorConfig
pre-commit hook
<https://github.com/editorconfig-checker/editorconfig-checker.python>`_.
"""

import os

import yaml

__PRECOMMIT_CONFIG_FILE = ".pre-commit-config.yaml"
__EDITORCONFIG_FILE = ".editorconfig"
__EDITORCONFIG_URL = (
    "https://github.com/editorconfig-checker/editorconfig-checker.python"
)
__EDITORCONFIG_HOOK = f"""
  - repo: {__EDITORCONFIG_URL}
    rev: ""
    hooks:
      - id: editorconfig-checker
"""


def check_editor_config_hook() -> None:
    if _has_editor_config() and not _has_precommit_hook():
        raise ValueError(
            f"This repository has an ./{__EDITORCONFIG_FILE} file, but its"
            f" ./{__PRECOMMIT_CONFIG_FILE} file contains no hook to enforce it."
            " Please add the following hook:\n"
            f"{__EDITORCONFIG_HOOK}\n"
            "and run pre-commit autoupdate"
        )


def _has_editor_config() -> bool:
    if not os.path.exists(__EDITORCONFIG_FILE):
        return False
    return True


def _has_precommit_hook() -> bool:
    if not os.path.exists(__PRECOMMIT_CONFIG_FILE):
        return False
    with open(__PRECOMMIT_CONFIG_FILE) as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    repos = config.get("repos")
    if repos is None:
        return False
    repos_urls = {repo.get("repo") for repo in repos if isinstance(repo, dict)}
    if __EDITORCONFIG_URL not in repos_urls:
        return False
    return True
