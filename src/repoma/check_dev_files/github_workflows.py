"""Check :file:`.github/workflows` folder content."""
import os
import re
from pathlib import Path
from typing import List, Tuple

from ruamel.yaml.main import YAML

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, write
from repoma.utilities.executor import Executor
from repoma.utilities.setup_cfg import get_pypi_name
from repoma.utilities.yaml import create_prettier_round_trip_yaml


def main(apt_packages: str, no_pypi: bool) -> None:
    executor = Executor()
    executor(_update_cd_workflow, no_pypi)
    executor(_update_ci_workflow, _format_apt_list(apt_packages))
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _format_apt_list(apt_packages: str) -> List[str]:
    """Create a list of APT packages from a string argument.

    >>> _format_apt_list('a c , test,b')
    ['a', 'b', 'c', 'test']
    """
    apt_packages = apt_packages.replace(",", " ")
    while "  " in apt_packages:
        apt_packages = apt_packages.replace("  ", " ")
    return sorted(apt_packages.split(" "))


def _update_cd_workflow(no_pypi: bool) -> None:
    def update() -> None:
        yaml = create_prettier_round_trip_yaml()
        cd = "cd.yml"  # pylint: disable=invalid-name
        expected_data = yaml.load(REPOMA_DIR / CONFIG_PATH.github_workflow_dir / cd)
        if no_pypi or not os.path.exists(CONFIG_PATH.setup_cfg):
            del expected_data["jobs"]["pypi"]

        workflow_path = CONFIG_PATH.github_workflow_dir / cd
        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    executor = Executor()
    executor(update)
    executor(remove_workflow, "milestone.yml")
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _update_ci_workflow(apt_packages: List[str]) -> None:
    def update() -> None:
        yaml, expected_data = _get_ci_workflow(
            REPOMA_DIR / CONFIG_PATH.github_workflow_dir / "ci.yml",
            apt_packages,
        )
        workflow_path = CONFIG_PATH.github_workflow_dir / "ci.yml"
        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    executor = Executor()
    executor(update)
    executor(remove_workflow, "ci-docs.yml")
    executor(remove_workflow, "ci-style.yml")
    executor(remove_workflow, "ci-tests.yml")
    executor(remove_workflow, "linkcheck.yml")
    executor(_copy_workflow_file, "clean-cache.yml")
    if executor.error_messages:
        raise PrecommitError(executor.merge_messages())


def _get_ci_workflow(path: Path, apt_packages: List[str]) -> Tuple[YAML, dict]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(path)
    # Configure `doc` job
    if not os.path.exists("docs/"):
        del config["jobs"]["doc"]
    else:
        with_section = config["jobs"]["doc"]["with"]
        if apt_packages:
            with_section["apt-packages"] = apt_packages
        if not os.path.exists(CONFIG_PATH.readthedocs):
            with_section["gh-pages"] = True
        if with_section == {}:
            del with_section
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
