"""Check existence of pre-commit hook for EditorConfig.

If a repository has an ``.editorconfig`` file, it should have an `EditorConfig
pre-commit hook
<https://github.com/editorconfig-checker/editorconfig-checker.python>`_.
"""

from functools import lru_cache
from textwrap import dedent

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import FoldedScalarString

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.precommit import find_repo, load_round_trip_precommit_config

__EDITORCONFIG_URL = (
    "https://github.com/editorconfig-checker/editorconfig-checker.python"
)


def main() -> None:
    if CONFIG_PATH.editorconfig.exists():
        _update_precommit_config()


def _update_precommit_config() -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    expected_hook = __get_expected_hook_definition()
    existing_config, yaml = load_round_trip_precommit_config()
    repos: CommentedSeq = existing_config.get("repos", [])
    idx_and_repo = find_repo(existing_config, __EDITORCONFIG_URL)
    if idx_and_repo is None:
        repos.append(expected_hook)
        idx = len(repos) - 1
        repos.yaml_set_comment_before_after_key(idx, before="\n")
        yaml.dump(existing_config, CONFIG_PATH.precommit)
        raise PrecommitError(f"Added editorconfig hook to {CONFIG_PATH.precommit}")
    idx, existing_hook = idx_and_repo
    if not __is_equivalent(existing_hook, expected_hook):
        existing_rev = existing_hook.get("rev")
        if existing_rev is not None:
            expected_hook["rev"] = existing_rev
        repos[idx] = expected_hook
        repos.yaml_set_comment_before_after_key(idx + 1, before="\n")
        yaml.dump(existing_config, CONFIG_PATH.precommit)
        raise PrecommitError(f"Updated editorconfig hook in {CONFIG_PATH.precommit}")


@lru_cache(maxsize=None)
def __get_expected_hook_definition() -> CommentedMap:
    excludes = R"""
    (?x)^(
      .*\.py
    )$
    """
    excludes = dedent(excludes).strip()
    hook = {
        "id": "editorconfig-checker",
        "name": "editorconfig",
        "alias": "ec",
        "exclude": FoldedScalarString(excludes),
    }
    dct = {
        "repo": __EDITORCONFIG_URL,
        "rev": "",
        "hooks": [CommentedMap(hook)],
    }
    return CommentedMap(dct)


def __is_equivalent(expected: CommentedMap, existing: CommentedMap) -> bool:
    def remove_rev(config: CommentedMap) -> dict:
        config_copy = dict(config)
        config_copy.pop("rev", None)
        return config_copy

    return remove_rev(expected) == remove_rev(existing)
