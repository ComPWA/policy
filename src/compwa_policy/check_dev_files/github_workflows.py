"""Check :file:`.github/workflows` folder content."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import (
    COMPWA_POLICY_DIR,
    CONFIG_PATH,
    hash_file,
    vscode,
    write,
)
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import PythonVersion, has_pyproject_package_name
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap
    from ruamel.yaml.main import YAML

    from compwa_policy.utilities.precommit import Precommit


def main(
    precommit: Precommit,
    *,
    allow_deprecated: bool,
    doc_apt_packages: list[str],
    environment_variables: dict[str, str],
    github_pages: bool,
    keep_pr_linting: bool,
    macos_python_version: PythonVersion | None,
    no_cd: bool,
    no_milestones: bool,
    no_project_board: bool,
    no_pypi: bool,
    no_version_branches: bool,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
) -> None:
    with Executor() as do:
        if no_cd:
            remove_workflow("cd.yml")
        else:
            do(_update_cd_workflow, no_milestones, no_pypi, no_version_branches)
        do(
            _update_ci_workflow,
            precommit,
            allow_deprecated,
            doc_apt_packages,
            environment_variables,
            github_pages,
            macos_python_version,
            python_version,
            single_threaded,
            skip_tests,
        )
        if not no_project_board:
            do(_copy_workflow_file, "add-issue-to-project.yml")
        if not keep_pr_linting:
            do(_update_pr_linting)
        do(_recommend_vscode_extension)


def _update_cd_workflow(  # noqa: C901
    no_milestones: bool, no_pypi: bool, no_version_branches: bool
) -> None:
    def update() -> None:  # noqa: C901
        yaml = create_prettier_round_trip_yaml()
        workflow_path = CONFIG_PATH.github_workflow_dir / "cd.yml"
        expected_data = yaml.load(COMPWA_POLICY_DIR / workflow_path)
        banned_jobs = set()
        if no_milestones:
            banned_jobs.add("milestone")
        if no_pypi or not has_pyproject_package_name():
            banned_jobs.add("package-name")
            banned_jobs.add("pypi")
        if no_version_branches:
            banned_jobs.add("push")
        if not expected_data["jobs"]:
            remove_workflow("cd.yml")
            return
        for name in banned_jobs:
            expected_data["jobs"].pop(name, None)
        if not expected_data["jobs"]:
            remove_workflow("cd.yml")
            return
        if not workflow_path.exists():
            update_workflow(yaml, expected_data, workflow_path)
        existing_data = yaml.load(workflow_path)
        for name, job_def in existing_data["jobs"].items():
            if name in banned_jobs:
                continue
            if name in expected_data["jobs"]:
                continue
            expected_data["jobs"][name] = job_def
        if existing_data != expected_data:
            update_workflow(yaml, expected_data, workflow_path)

    with Executor() as do:
        do(update)
        do(remove_workflow, "milestone.yml")


def _update_pr_linting() -> None:
    filename = "pr-linting.yml"
    input_path = COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / filename
    output_path = CONFIG_PATH.github_workflow_dir / filename
    output_path.parent.mkdir(exist_ok=True)
    if not output_path.exists() or hash_file(input_path) != hash_file(output_path):
        shutil.copyfile(input_path, output_path)
        msg = f"Updated {output_path} workflow"
        raise PrecommitError(msg)


def _update_ci_workflow(  # noqa: PLR0917
    precommit: Precommit,
    allow_deprecated: bool,
    doc_apt_packages: list[str],
    environment_variables: dict[str, str],
    github_pages: bool,
    macos_python_version: PythonVersion | None,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
) -> None:
    def update() -> None:
        yaml, expected_data = _get_ci_workflow(
            COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / "ci.yml",
            precommit,
            doc_apt_packages,
            environment_variables,
            github_pages,
            macos_python_version,
            python_version,
            single_threaded,
            skip_tests,
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

    with Executor() as do:
        do(update)
        if not allow_deprecated:
            do(remove_workflow, "ci-docs.yml")
            do(remove_workflow, "ci-style.yml")
            do(remove_workflow, "ci-tests.yml")
            do(remove_workflow, "linkcheck.yml")
        do(_copy_workflow_file, "clean-caches.yml")
        do(remove_workflow, "clean-cache.yml")


def _get_ci_workflow(  # noqa: PLR0917
    path: Path,
    precommit: Precommit,
    doc_apt_packages: list[str],
    environment_variables: dict[str, str],
    github_pages: bool,
    macos_python_version: PythonVersion | None,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
) -> tuple[YAML, dict]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(path)
    __update_env_section(config, environment_variables)
    __update_doc_section(config, doc_apt_packages, python_version, github_pages)
    __update_pytest_section(config, macos_python_version, single_threaded, skip_tests)
    __update_style_section(config, python_version, precommit)
    return yaml, config


def __update_env_section(
    config: CommentedMap, environment_variables: dict[str, str]
) -> None:
    env = cast("dict[str, str] | None", config.get("env"))
    if env is not None:
        env.clear()
        for key, value in environment_variables.items():
            env[key] = value
        if not env:
            del config["env"]


def __update_doc_section(
    config: CommentedMap,
    apt_packages: list[str],
    python_version: PythonVersion,
    github_pages: bool,
) -> None:
    if not os.path.exists("docs/"):
        del config["jobs"]["doc"]
    else:
        with_section = {}
        if python_version != DEFAULT_DEV_PYTHON_VERSION:
            with_section["python-version"] = DoubleQuotedScalarString(python_version)
        if apt_packages:
            with_section["apt-packages"] = " ".join(apt_packages)
        if not CONFIG_PATH.readthedocs.exists() or github_pages:
            with_section["gh-pages"] = True
        if with_section:
            config["jobs"]["doc"]["with"] = with_section
        __update_with_section(config, job_name="doc")


def __update_style_section(
    config: CommentedMap, python_version: PythonVersion, precommit: Precommit
) -> None:
    if python_version != DEFAULT_DEV_PYTHON_VERSION:
        config["jobs"]["style"]["with"] = {
            "python-version": DoubleQuotedScalarString(python_version)
        }
    if __is_remove_style_job(precommit):
        del config["jobs"]["style"]


def __is_remove_style_job(precommit: Precommit) -> bool:
    precommit_ci = precommit.document.get("ci")
    return precommit_ci is not None and "skip" not in precommit_ci


def __update_pytest_section(
    config: CommentedMap,
    macos_python_version: PythonVersion | None,
    single_threaded: bool,
    skip_tests: list[str],
) -> None:
    test_dir = "tests"
    if not os.path.exists(test_dir):
        del config["jobs"]["test"]
    else:
        with_section = {}
        if CONFIG_PATH.codecov.exists():
            with_section["coverage-python-version"] = __get_coverage_python_version()
            secrets = {
                "CODECOV_TOKEN": "${{ secrets.CODECOV_TOKEN }}",
            }
            config["jobs"]["test"]["secrets"] = secrets
        if macos_python_version is not None:
            with_section["macos-python-version"] = DoubleQuotedScalarString(
                macos_python_version
            )
        if skip_tests:
            with_section["skipped-python-versions"] = " ".join(skip_tests)
        if single_threaded:
            with_section["multithreaded"] = False
        output_path = f"{test_dir}/output/"
        if os.path.exists(output_path):
            with_section["test-output-path"] = output_path
        if with_section:
            config["jobs"]["test"]["with"] = with_section
        __update_with_section(config, job_name="test")


def __update_with_section(config: dict, job_name: str) -> None:
    with_section = config["jobs"][job_name]["with"]
    if with_section:
        sorted_section = {k: with_section[k] for k in sorted(with_section)}
        config["jobs"][job_name]["with"] = sorted_section
    else:
        del with_section


def __get_coverage_python_version() -> PythonVersion:
    python_version_file = Path(".python-version")
    if python_version_file.exists():
        return python_version_file.read_text().strip()  # ty:ignore[invalid-return-type]
    return DEFAULT_DEV_PYTHON_VERSION


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
        msg = f"Created {workflow_path} workflow"
        raise PrecommitError(msg)

    with open(workflow_path) as stream:
        existing_content = stream.read()
    if existing_content != expected_content:
        write(expected_content, target=workflow_path)
        msg = f"Updated {workflow_path} workflow"
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
    with Executor() as do:
        do(vscode.remove_extension_recommendation, "cschleiden.vscode-github-actions")
        do(vscode.add_extension_recommendation, "github.vscode-github-actions")
        ci_workflow = CONFIG_PATH.github_workflow_dir / "ci.yml"
        if ci_workflow.exists():
            action_settings = {
                "github-actions.workflows.pinned.workflows": [str(ci_workflow)],
            }
            vscode.update_settings(action_settings)


def remove_workflow(filename: str) -> None:
    path = CONFIG_PATH.github_workflow_dir / filename
    if path.exists():
        path.unlink()
        msg = f"Removed deprecated {filename} workflow"
        raise PrecommitError(msg)


def update_workflow(yaml: YAML, config: dict, path: Path) -> None:
    path.parent.mkdir(exist_ok=True, parents=True)
    yaml.dump(config, path)
    verb = "Updated" if path.exists() else "Created"
    msg = f"{verb} {path} workflow"
    raise PrecommitError(msg)
