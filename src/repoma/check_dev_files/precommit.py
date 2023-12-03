"""Check content of :code:`.pre-commit-config.yaml` and related files."""

from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import PrecommitConfig
from repoma.utilities.yaml import create_prettier_round_trip_yaml


def main() -> None:
    cfg = PrecommitConfig.load()
    executor = Executor()
    executor(_sort_hooks)
    executor(_update_conda_environment, cfg)
    executor(_update_precommit_ci_skip, cfg)
    executor.finalize()


def _sort_hooks() -> None:
    yaml = create_prettier_round_trip_yaml()
    contents: CommentedMap = yaml.load(CONFIG_PATH.precommit)
    repos: Optional[CommentedSeq] = contents.get("repos")
    if repos is None:
        return
    sorted_repos: List[CommentedMap] = sorted(repos, key=__repo_def_sorting)
    contents["repos"] = sorted_repos
    if sorted_repos != repos:
        yaml.dump(contents, CONFIG_PATH.precommit)
        msg = f"Sorted pre-commit hooks in {CONFIG_PATH.precommit}"
        raise PrecommitError(msg)


def __repo_def_sorting(repo_def: CommentedMap) -> Tuple[int, str]:
    if repo_def["repo"] == "meta":
        return (0, "meta")
    hooks: CommentedSeq = repo_def["hooks"]
    if len(hooks) > 1:
        return 1, repo_def["repo"]
    return (2, hooks[0]["id"])


def _update_precommit_ci_skip(config: PrecommitConfig) -> None:
    if config.ci is None:
        return
    local_hooks = get_local_hooks(config)
    non_functional_hooks = get_non_functional_hooks(config)
    expected_skips = set(non_functional_hooks) | set(local_hooks)
    if not expected_skips:
        if config.ci.skip is not None:
            yaml = create_prettier_round_trip_yaml()
            contents: CommentedMap = yaml.load(CONFIG_PATH.precommit)
            del contents["ci"]["skip"]
            contents.yaml_set_comment_before_after_key("repos", before="\n")
            yaml.dump(contents, CONFIG_PATH.precommit)
            msg = f"No need for a ci.skip in {CONFIG_PATH.precommit}"
            raise PrecommitError(msg)
        return
    existing_skips = __get_precommit_ci_skips(config)
    if existing_skips != expected_skips:
        __update_precommit_ci_skip(expected_skips)


def __update_precommit_ci_skip(expected_skips: Iterable[str]) -> None:
    yaml = create_prettier_round_trip_yaml()
    contents = yaml.load(CONFIG_PATH.precommit)
    ci_section: CommentedMap = contents["ci"]
    if "skip" in ci_section.ca.items:
        del ci_section.ca.items["skip"]
    skips = CommentedSeq(sorted(expected_skips))
    ci_section["skip"] = skips
    contents.yaml_set_comment_before_after_key("repos", before="\n")
    yaml.dump(contents, CONFIG_PATH.precommit)
    msg = f"Updated ci.skip section in {CONFIG_PATH.precommit}"
    raise PrecommitError(msg)


def __get_precommit_ci_skips(config: PrecommitConfig) -> Set[str]:
    if config.ci is None:
        msg = "Pre-commit config does not contain a ci section"
        raise ValueError(msg)
    if config.ci.skip is None:
        return set()
    return set(config.ci.skip)


def get_local_hooks(config: PrecommitConfig) -> List[str]:
    return [h.id for r in config.repos for h in r.hooks if r.repo == "local"]


def get_non_functional_hooks(config: PrecommitConfig) -> List[str]:
    return [
        hook.id
        for repo in config.repos
        for hook in repo.hooks
        if repo.repo
        if hook.id in __get_skipped_hooks(config)
    ]


def _update_conda_environment(precommit_config: PrecommitConfig) -> None:
    """Temporary fix for Prettier v4 alpha releases.

    https://prettier.io/blog/2023/11/30/cli-deep-dive#installation
    """
    path = Path("environment.yml")
    if not path.exists():
        return
    yaml = create_prettier_round_trip_yaml()
    conda_env: CommentedMap = yaml.load(path)
    variables: CommentedMap = conda_env.get("variables", {})
    key = "PRETTIER_LEGACY_CLI"
    if __has_prettier_v4alpha(precommit_config):
        if key not in variables:
            variables[key] = DoubleQuotedScalarString("1")
            conda_env["variables"] = variables
            yaml.dump(conda_env, path)
            msg = f"Set {key} environment variable in {path}"
            raise PrecommitError(msg)
    elif key in variables:
        del variables[key]
        if not variables:
            del conda_env["variables"]
        yaml.dump(conda_env, path)
        msg = f"Removed {key} environment variable {path}"
        raise PrecommitError(msg)


def __get_skipped_hooks(config: PrecommitConfig) -> Set[str]:
    skipped_hooks = {
        "check-jsonschema",
        "pyright",
        "taplo",
    }
    if __has_prettier_v4alpha(config):
        skipped_hooks.add("prettier")
    return skipped_hooks


def __has_prettier_v4alpha(config: PrecommitConfig) -> bool:
    repo = config.find_repo(r"^.*/mirrors-prettier$")
    if repo is None:
        return False
    if repo.rev is None:
        return False
    rev = repo.rev
    return rev.startswith("v4") and "alpha" in rev
