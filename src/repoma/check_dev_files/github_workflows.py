"""Check :file:`.github/workflows` folder content."""
import os
import re
from pathlib import Path
from typing import Tuple

from ruamel.yaml.main import YAML

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, write
from repoma.utilities.executor import Executor
from repoma.utilities.setup_cfg import get_pypi_name
from repoma.utilities.yaml import create_prettier_round_trip_yaml


def main(no_cd: bool) -> None:
    executor = Executor()
    executor(_update_ci_workflow)
    if not no_cd:
        executor(_check_milestone_workflow)
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _update_ci_workflow() -> None:
    yaml, expected_data = _get_ci_workflow(
        path=REPOMA_DIR / CONFIG_PATH.github_workflow_dir / "ci.yml"
    )
    workflow_path = CONFIG_PATH.github_workflow_dir / "ci.yml"
    if not workflow_path.exists():
        update_workflow(yaml, expected_data, workflow_path)
    existing_data = yaml.load(workflow_path)
    if existing_data != expected_data:
        update_workflow(yaml, expected_data, workflow_path)

    remove_workflow("ci-docs.yml")
    remove_workflow("ci-style.yml")
    remove_workflow("ci-tests.yml")
    remove_workflow("linkcheck.yml")


def _get_ci_workflow(path: Path) -> Tuple[YAML, dict]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(path)
    # Configure `doc` job
    if not os.path.exists("docs/"):
        del config["jobs"]["doc"]
    elif os.path.exists(CONFIG_PATH.readthedocs):
        del config["jobs"]["doc"]["with"]
    # Configure `pytest` job
    if not os.path.exists("tests"):
        del config["jobs"]["pytest"]
    elif os.path.exists(CONFIG_PATH.codecov):
        package_name = get_pypi_name().replace("-", "_")
        config["jobs"]["pytest"]["with"]["coverage-target"] = package_name
    # Configure `style` job
    if not os.path.exists(CONFIG_PATH.precommit):
        del config["jobs"]["style"]
    return yaml, config


def create_continuous_deployment() -> None:
    _copy_workflow_file("cd.yml")


def _check_milestone_workflow() -> None:
    """Add a GitHub Action that auto-closes milestones on a new release.

    See `github.com/mhutchie/update-milestone-on-release
    <https://github.com/mhutchie/update-milestone-on-release>`_.
    """
    # cspell:ignore mhutchie
    _copy_workflow_file("milestone.yml")


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


def remove_workflow(filename: str) -> None:
    path = CONFIG_PATH.github_workflow_dir / filename
    if path.exists():
        path.unlink()
        raise PrecommitError(f'Removed deprecated "{filename}" workflow')


def update_workflow(yaml: YAML, config: dict, path: Path) -> None:
    yaml.dump(config, path)
    raise PrecommitError(f'Updated "{path}" workflow')
