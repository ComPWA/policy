"""Check :file:`.github/workflows` folder content."""

from __future__ import annotations

import os
import re
import shutil
from typing import TYPE_CHECKING

from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import (
    COMPWA_POLICY_DIR,
    CONFIG_PATH,
    hash_file,
    vscode,
    write,
)
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import load_round_trip_precommit_config
from compwa_policy.utilities.project_info import PythonVersion, get_pypi_name
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from pathlib import Path

    from ruamel.yaml.comments import CommentedMap
    from ruamel.yaml.main import YAML


def main(
    allow_deprecated: bool,
    doc_apt_packages: list[str],
    no_macos: bool,
    no_pypi: bool,
    no_version_branches: bool,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
    test_extras: list[str],
) -> None:
    executor = Executor()
    executor(_update_cd_workflow, no_pypi, no_version_branches)
    executor(
        _update_ci_workflow,
        allow_deprecated,
        doc_apt_packages,
        no_macos,
        python_version,
        single_threaded,
        skip_tests,
        test_extras,
    )
    executor(_update_pr_linting)
    executor(_recommend_vscode_extension)
    executor.finalize()


def _update_cd_workflow(no_pypi: bool, no_version_branches: bool) -> None:
    def update() -> None:
        yaml = create_prettier_round_trip_yaml()
        workflow_path = CONFIG_PATH.github_workflow_dir / "cd.yml"
        expected_data = yaml.load(COMPWA_POLICY_DIR / workflow_path)
        if no_pypi or not CONFIG_PATH.setup_cfg.exists():
            del expected_data["jobs"]["pypi"]
        if no_version_branches:
            del expected_data["jobs"]["push"]
        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        for name, job_def in existing_data["jobs"].items():
            if name not in expected_data["jobs"]:
                expected_data["jobs"][name] = job_def
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    executor = Executor()
    executor(update)
    executor(remove_workflow, "milestone.yml")
    executor.finalize()


def _update_pr_linting() -> None:
    filename = "pr-linting.yml"
    input_path = COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / filename
    output_path = CONFIG_PATH.github_workflow_dir / filename
    output_path.parent.mkdir(exist_ok=True)
    if not output_path.exists() or hash_file(input_path) != hash_file(output_path):
        shutil.copyfile(input_path, output_path)
        msg = f'Updated "{output_path}" workflow'
        raise PrecommitError(msg)


def _update_ci_workflow(
    allow_deprecated: bool,
    doc_apt_packages: list[str],
    no_macos: bool,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
    test_extras: list[str],
) -> None:
    def update() -> None:
        yaml, expected_data = _get_ci_workflow(
            COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / "ci.yml",
            doc_apt_packages,
            no_macos,
            python_version,
            single_threaded,
            skip_tests,
            test_extras,
        )
        workflow_path = CONFIG_PATH.github_workflow_dir / "ci.yml"
        if not expected_data.get("jobs"):
            if workflow_path.exists():
                workflow_path.unlink()
                msg = "Removed redundant CI workflows"
                raise PrecommitError(msg)
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
    doc_apt_packages: list[str],
    no_macos: bool,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
    test_extras: list[str],
) -> tuple[YAML, dict]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(path)
    __update_doc_section(config, doc_apt_packages, python_version)
    __update_pytest_section(config, no_macos, single_threaded, skip_tests, test_extras)
    __update_style_section(config, python_version)
    return yaml, config


def __update_doc_section(
    config: CommentedMap, apt_packages: list[str], python_version: PythonVersion
) -> None:
    if not os.path.exists("docs/"):
        del config["jobs"]["doc"]
    else:
        with_section = config["jobs"]["doc"]["with"]
        if python_version != "3.8":
            with_section["python-version"] = DoubleQuotedScalarString(python_version)
        if apt_packages:
            with_section["apt-packages"] = " ".join(apt_packages)
        if not CONFIG_PATH.readthedocs.exists():
            with_section["gh-pages"] = True
        __update_with_section(config, job_name="doc")


def __update_style_section(config: CommentedMap, python_version: PythonVersion) -> None:
    if python_version != "3.8":
        config["jobs"]["style"]["with"] = {
            "python-version": DoubleQuotedScalarString(python_version)
        }
    if __is_remove_style_job():
        del config["jobs"]["style"]


def __is_remove_style_job() -> bool:
    if not CONFIG_PATH.precommit.exists():
        return True
    cfg, _ = load_round_trip_precommit_config()
    precommit_ci = cfg.get("ci")
    if precommit_ci is not None and "skip" not in precommit_ci:
        return True
    return False


def __update_pytest_section(
    config: CommentedMap,
    no_macos: bool,
    single_threaded: bool,
    skip_tests: list[str],
    test_extras: list[str],
) -> None:
    test_dir = "tests"
    if not os.path.exists(test_dir):
        del config["jobs"]["pytest"]
    else:
        with_section = config["jobs"]["pytest"]["with"]
        if test_extras:
            with_section["additional-extras"] = ",".join(test_extras)
        if CONFIG_PATH.codecov.exists():
            with_section["coverage-target"] = __get_package_name()
        if not no_macos:
            with_section["macos-python-version"] = DoubleQuotedScalarString("3.9")
        if skip_tests:
            with_section["skipped-python-versions"] = " ".join(skip_tests)
        if single_threaded:
            with_section["multithreaded"] = False
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
    candidate_dirs = [
        s
        for s in src_dirs
        if s.startswith(pypi_name[0].lower())
        if not s.endswith(".egg-info")
    ]
    if candidate_dirs:
        return sorted(candidate_dirs)[0]
    return sorted(src_dirs)[0]


def _copy_workflow_file(filename: str) -> None:
    expected_workflow_path = (
        COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / filename
    )
    with open(expected_workflow_path) as stream:
        expected_content = stream.read()
    if not CONFIG_PATH.pip_constraints.exists():
        expected_content = __remove_constraint_pinning(expected_content)

    workflow_path = f"{CONFIG_PATH.github_workflow_dir}/{filename}"
    if not os.path.exists(workflow_path):
        write(expected_content, target=workflow_path)
        msg = f'Created "{workflow_path}" workflow'
        raise PrecommitError(msg)

    with open(workflow_path) as stream:
        existing_content = stream.read()
    if existing_content != expected_content:
        write(expected_content, target=workflow_path)
        msg = f'Updated "{workflow_path}" workflow'
        raise PrecommitError(msg)


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
    executor(vscode.remove_extension_recommendation, "cschleiden.vscode-github-actions")
    executor(vscode.add_extension_recommendation, "github.vscode-github-actions")
    ci_workflow = CONFIG_PATH.github_workflow_dir / "ci.yml"
    if ci_workflow.exists():
        action_settings = {
            "github-actions.workflows.pinned.workflows": [str(ci_workflow)],
        }
        vscode.update_settings(action_settings)
    executor.finalize()


def remove_workflow(filename: str) -> None:
    path = CONFIG_PATH.github_workflow_dir / filename
    if path.exists():
        path.unlink()
        msg = f'Removed deprecated "{filename}" workflow'
        raise PrecommitError(msg)


def update_workflow(yaml: YAML, config: dict, path: Path) -> None:
    path.parent.mkdir(exist_ok=True, parents=True)
    yaml.dump(config, path)
    verb = "Updated" if path.exists() else "Created"
    msg = f'{verb} "{path}" workflow'
    raise PrecommitError(msg)
