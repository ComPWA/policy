"""Check :file:`.github/workflows` folder content."""
import os
import re
from pathlib import Path
from typing import List, Tuple

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.main import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR, write
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import PrecommitConfig
from repoma.utilities.setup_cfg import get_pypi_name
from repoma.utilities.vscode import (
    add_extension_recommendation,
    remove_extension_recommendation,
)
from repoma.utilities.yaml import create_prettier_round_trip_yaml


def main(  # pylint: disable=too-many-arguments
    allow_deprecated: bool,
    doc_apt_packages: List[str],
    no_macos: bool,
    no_pypi: bool,
    skip_tests: List[str],
    test_extras: List[str],
) -> None:
    executor = Executor()
    executor(_update_cd_workflow, no_pypi)
    executor(
        _update_ci_workflow,
        allow_deprecated,
        doc_apt_packages,
        no_macos,
        skip_tests,
        test_extras,
    )
    executor(_recommend_vscode_extension)
    executor.finalize()


def _update_cd_workflow(no_pypi: bool) -> None:
    def update() -> None:
        yaml = create_prettier_round_trip_yaml()
        workflow_path = CONFIG_PATH.github_workflow_dir / "cd.yml"
        expected_data = yaml.load(REPOMA_DIR / workflow_path)
        if no_pypi or not os.path.exists(CONFIG_PATH.setup_cfg):
            del expected_data["jobs"]["pypi"]

        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    executor = Executor()
    executor(update)
    executor(remove_workflow, "milestone.yml")
    executor.finalize()


def _update_ci_workflow(
    allow_deprecated: bool,
    doc_apt_packages: List[str],
    no_macos: bool,
    skip_tests: List[str],
    test_extras: List[str],
) -> None:
    def update() -> None:
        yaml, expected_data = _get_ci_workflow(
            REPOMA_DIR / CONFIG_PATH.github_workflow_dir / "ci.yml",
            doc_apt_packages,
            no_macos,
            skip_tests,
            test_extras,
        )
        workflow_path = CONFIG_PATH.github_workflow_dir / "ci.yml"
        if not expected_data.get("jobs"):
            if workflow_path.exists():
                workflow_path.unlink()
                raise PrecommitError("Removed redundant CI workflows")
        else:
            if not workflow_path.exists():
                update_workflow(yaml, expected_data, workflow_path)
            existing_data = yaml.load(workflow_path)
            if existing_data != expected_data:
                update_workflow(yaml, expected_data, workflow_path)

    executor = Executor()
    executor(update)
    if not allow_deprecated:
        executor(remove_workflow, "ci-docs.yml")
        executor(remove_workflow, "ci-style.yml")
        executor(remove_workflow, "ci-tests.yml")
        executor(remove_workflow, "linkcheck.yml")
    executor(_copy_workflow_file, "clean-caches.yml")
    executor(remove_workflow, "clean-cache.yml")
    executor.finalize()


def _get_ci_workflow(
    path: Path,
    doc_apt_packages: List[str],
    no_macos: bool,
    skip_tests: List[str],
    test_extras: List[str],
) -> Tuple[YAML, dict]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(path)
    __update_doc_section(config, doc_apt_packages)
    __update_pytest_section(config, no_macos, skip_tests, test_extras)
    __update_style_section(config)
    return yaml, config


def __update_doc_section(config: CommentedMap, apt_packages: List[str]) -> None:
    if not os.path.exists("docs/"):
        del config["jobs"]["doc"]
    else:
        with_section = config["jobs"]["doc"]["with"]
        if apt_packages:
            with_section["apt-packages"] = " ".join(apt_packages)
        if not os.path.exists(CONFIG_PATH.readthedocs):
            with_section["gh-pages"] = True
        __update_with_section(config, job_name="doc")


def __update_style_section(config: CommentedMap) -> None:
    if not os.path.exists(CONFIG_PATH.precommit):
        del config["jobs"]["style"]
    else:
        cfg = PrecommitConfig.load()
        if cfg.ci is not None and cfg.ci.skip is None:
            del config["jobs"]["style"]


def __update_pytest_section(
    config: CommentedMap, no_macos: bool, skip_tests: List[str], test_extras: List[str]
) -> None:
    test_dir = "tests"
    if not os.path.exists(test_dir):
        del config["jobs"]["pytest"]
    else:
        with_section = config["jobs"]["pytest"]["with"]
        if test_extras:
            with_section["additional-extras"] = ",".join(test_extras)
        if os.path.exists(CONFIG_PATH.codecov):
            with_section["coverage-target"] = __get_package_name()
        if not no_macos:
            with_section["macos-python-version"] = DoubleQuotedScalarString("3.7")
        if skip_tests:
            with_section["skipped-python-versions"] = " ".join(skip_tests)
        output_path = f"{test_dir}/output/"
        if os.path.exists(output_path):
            with_section["test-output-path"] = output_path
        __update_with_section(config, job_name="pytest")


def __update_with_section(config: dict, job_name: str) -> None:
    with_section = config["jobs"][job_name]["with"]
    if with_section:
        sorted_section = {k: with_section[k] for k in sorted(with_section)}
        config["jobs"][job_name]["with"] = sorted_section
    else:
        del with_section


def __get_package_name() -> str:
    pypi_name = get_pypi_name()
    package_name = pypi_name.replace("-", "_").lower()
    if os.path.exists(f"src/{package_name}/"):
        return package_name
    src_dirs = os.listdir("src/")
    candidate_dirs = [s for s in src_dirs if s.startswith(pypi_name[0].lower())]
    if candidate_dirs:
        return sorted(candidate_dirs)[0]
    return sorted(src_dirs)[0]


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


def _recommend_vscode_extension() -> None:
    if not CONFIG_PATH.github_workflow_dir.exists():
        return
    # cspell:ignore cschleiden
    executor = Executor()
    executor(remove_extension_recommendation, "cschleiden.vscode-github-actions")
    executor(add_extension_recommendation, "github.vscode-github-actions")
    executor.finalize()


def remove_workflow(filename: str) -> None:
    path = CONFIG_PATH.github_workflow_dir / filename
    if path.exists():
        path.unlink()
        raise PrecommitError(f'Removed deprecated "{filename}" workflow')


def update_workflow(yaml: YAML, config: dict, path: Path) -> None:
    path.parent.mkdir(exist_ok=True)
    yaml.dump(config, path)
    verb = "Updated" if path.exists() else "Created"
    raise PrecommitError(f'{verb} "{path}" workflow')
