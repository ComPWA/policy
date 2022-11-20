"""Check :file:`.github/workflows` folder content."""

import os
import re
from typing import Iterable, List

from ruamel.yaml import YAML

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, write
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import PrecommitConfig
from repoma.utilities.yaml import create_prettier_round_trip_yaml

from .precommit import get_local_hooks, get_non_functional_hooks

__STYLE_WORKFLOW = "ci-style.yml"


def main(no_docs: bool, no_cd: bool) -> None:
    executor = Executor()
    if not no_cd:
        executor(_check_milestone_workflow)
    if not no_docs:
        executor(_check_docs_workflow)
    if os.path.exists(CONFIG_PATH.precommit):
        executor(_check_style_workflow)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def create_continuous_deployment() -> None:
    _copy_workflow_file("cd.yml")


def _check_milestone_workflow() -> None:
    """Add a GitHub Action that auto-closes milestones on a new release.

    See `github.com/mhutchie/update-milestone-on-release
    <https://github.com/mhutchie/update-milestone-on-release>`_.
    """
    # cspell:ignore mhutchie
    _copy_workflow_file("milestone.yml")


def _check_docs_workflow() -> None:
    if os.path.exists("./docs/") or os.path.exists("./doc/"):
        executor = Executor()
        executor(_copy_workflow_file, "ci-docs.yml")
        executor(_copy_workflow_file, "linkcheck.yml")
        if executor.error_messages:
            raise PrecommitError(executor.merge_messages())


def _check_style_workflow() -> None:
    precommit = PrecommitConfig.load()
    if precommit.ci is not None and precommit.ci.skip is None:
        return
    yaml = create_prettier_round_trip_yaml()
    expected = __get_expected_style_workflow(precommit, yaml)
    output_path = CONFIG_PATH.github_workflow_dir / __STYLE_WORKFLOW
    if not os.path.exists(output_path):
        yaml.dump(expected, output_path)
        raise PrecommitError(f"Created {output_path}")
    existing = yaml.load(output_path)
    if existing != expected:
        yaml.dump(expected, output_path)
        raise PrecommitError(f"Updated {output_path}")


def __get_expected_style_workflow(  # noqa: R701
    precommit: PrecommitConfig, yaml: YAML
) -> dict:
    workflow = yaml.load(REPOMA_DIR / ".template" / __STYLE_WORKFLOW)
    steps: List[dict] = workflow["jobs"]["style"]["steps"]
    local_hooks = get_local_hooks(precommit)
    non_functional_hooks = get_non_functional_hooks(precommit)
    if "mypy" not in set(local_hooks):
        paths: List[str] = steps[1]["with"]["path"].split("\n")
        paths.pop(0)
        steps[1]["with"]["path"] = "\n".join(paths)
    constraint_file = CONFIG_PATH.pip_constraints / "py3.8.txt"
    if os.path.exists(constraint_file):
        cmd: str = steps[3]["run"]
        steps[3]["run"] = cmd.replace("-e .[sty]", f"-c {constraint_file} -e .[sty]")
    if local_hooks:
        steps[4]["run"] = __to_commands(local_hooks)
    if non_functional_hooks:
        steps[5]["run"] = __to_commands(non_functional_hooks)
    if not local_hooks or not non_functional_hooks:
        if not local_hooks and not non_functional_hooks:
            steps.pop(4)
            steps.pop(5)
        elif not local_hooks:
            steps.pop(4)
        elif not non_functional_hooks:
            steps.pop(5)
    return workflow


def __to_commands(hook_ids: Iterable[str]) -> str:
    """Create pre-commit commands.

    >>> print(__to_commands(["pyright", "mypy"]))
    pre-commit run mypy -a --color always
    pre-commit run pyright -a --color always
    """
    commands = [f"pre-commit run {h} -a --color always" for h in sorted(hook_ids)]
    return "\n".join(commands)


def _copy_workflow_file(filename: str) -> None:
    expected_workflow_path = REPOMA_DIR / CONFIG_PATH.github_workflow_dir / filename
    with open(expected_workflow_path) as stream:
        expected_content = stream.read()
    if not CONFIG_PATH.pip_constraints.exists():
        expected_content = __remove_constraint_pinning(expected_content)

    workflow_path = f"{CONFIG_PATH.github_workflow_dir}/{filename}"
    if not os.path.exists(workflow_path):
        write(expected_content, target=workflow_path)
        raise PrecommitError(f'Created "{workflow_path}" workflow')

    with open(workflow_path) as stream:
        existing_content = stream.read()
    if existing_content != expected_content:
        write(expected_content, target=workflow_path)
        raise PrecommitError(f'Updated "{workflow_path}" workflow')


def __remove_constraint_pinning(content: str) -> str:
    """Remove constraint flags from a pip install statement.

    >>> src = "pip install -c .constraints/py3.7.txt .[dev]"
    >>> __remove_constraint_pinning(src)
    'pip install .[dev]'
    """
    return re.sub(
        pattern=rf"-c {CONFIG_PATH.pip_constraints}/py3\.\d\.txt\s*",
        repl="",
        string=content,
    )
