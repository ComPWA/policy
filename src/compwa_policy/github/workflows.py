"""Check :file:`.github/workflows` folder content."""

from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from compwa_policy import _to_list
from compwa_policy.characterization import has_documentation, has_notebooks
from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, vscode
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.pyproject import PythonVersion, has_pyproject_package_name
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap
    from ruamel.yaml.main import YAML

    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.precommit import Precommit
    from compwa_policy.utilities.session import Changelog, Session


@check_hook(
    group="github",
    paths=[
        CONFIG_PATH.codecov,
        CONFIG_PATH.precommit,
        CONFIG_PATH.pyproject,
        CONFIG_PATH.readthedocs,
        ".python-version",
    ],
    directories=(CONFIG_PATH.github_workflow_dir.parent, CONFIG_PATH.pip_constraints),
    enabled=lambda args, _ctx: not args.no_github_actions,
)
def check(session: Session, args: Arguments, ctx: CheckContext) -> None:
    repository = f"{args.repo_organization}/{args.repo_name}"
    if args.no_cd:
        session.changelog += remove_workflow("cd.yml")
    else:
        _update_cd_workflow(
            session,
            args.no_milestones,
            args.no_pypi,
            args.no_version_branches,
            repository,
        )
    _update_ci_workflow(
        session,
        args.allow_deprecated_workflows,
        ctx.doc_apt_packages,
        ctx.environment_variables,
        args.github_pages,
        args.macos_python_version,
        args.dev_python_version,
        args.pytest_single_threaded,
        _to_list(args.ci_skipped_tests),
        repository,
    )
    if not args.keep_pr_linting:
        copy_workflow_file(session, filename="pr-linting.yml", repository=repository)
    _recommend_vscode_extension(session)


def _update_cd_workflow(  # ruff: ignore[complex-structure]
    session: Session,
    /,
    no_milestones: bool,
    no_pypi: bool,
    no_version_branches: bool,
    repository: str,
) -> None:
    def update() -> Changelog:  # ruff: ignore[complex-structure]
        yaml = create_prettier_round_trip_yaml()
        workflow_path = CONFIG_PATH.github_workflow_dir / "cd.yml"
        expected_data = yaml.load(COMPWA_POLICY_DIR / workflow_path)
        banned_jobs = set()
        if no_milestones:
            banned_jobs.add("milestone")
        if no_pypi or not has_pyproject_package_name(session):
            banned_jobs.add("package-name")
            banned_jobs.add("pypi")
        if no_version_branches:
            banned_jobs.add("push")
        if not expected_data["jobs"]:
            return remove_workflow("cd.yml")
        for name in banned_jobs:
            expected_data["jobs"].pop(name, None)
        if not expected_data["jobs"]:
            return remove_workflow("cd.yml")
        if not workflow_path.exists():
            return update_workflow(
                yaml, expected_data, workflow_path, repository=repository
            )
        existing_data = yaml.load(workflow_path)
        for name, job_def in existing_data["jobs"].items():
            if name in banned_jobs:
                continue
            if name in expected_data["jobs"]:
                continue
            expected_data["jobs"][name] = job_def
        if existing_data != expected_data:
            return update_workflow(
                yaml, expected_data, workflow_path, repository=repository
            )
        return []

    session.changelog += update()
    session.changelog += remove_workflow("milestone.yml")


def _update_ci_workflow(  # ruff: ignore[too-many-positional-arguments]
    session: Session,
    /,
    allow_deprecated: bool,
    doc_apt_packages: list[str],
    environment_variables: dict[str, str],
    github_pages: bool,
    macos_python_version: PythonVersion | None,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
    repository: str,
) -> None:
    def update() -> Changelog:
        precommit = session.precommit
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
                return ["Removed redundant CI workflows"]
        else:
            if not workflow_path.exists():
                return update_workflow(
                    yaml, expected_data, workflow_path, repository=repository
                )
            existing_data = yaml.load(workflow_path)
            if existing_data != expected_data:
                return update_workflow(
                    yaml, expected_data, workflow_path, repository=repository
                )
        return []

    session.changelog += update()
    if not allow_deprecated:
        session.changelog += remove_workflow("ci-docs.yml")
        session.changelog += remove_workflow("ci-style.yml")
        session.changelog += remove_workflow("ci-tests.yml")
        session.changelog += remove_workflow("linkcheck.yml")
    copy_workflow_file(session, filename="clean-caches.yml", repository=repository)
    session.changelog += remove_workflow("clean-cache.yml")


def _get_ci_workflow(  # ruff: ignore[too-many-positional-arguments]
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
    if has_documentation():
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
    else:
        del config["jobs"]["doc"]


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
    outsource_to_precommit = precommit_ci is not None and "skip" not in precommit_ci
    repository_has_notebooks = has_notebooks()
    return outsource_to_precommit and not repository_has_notebooks


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
    with_section = config["jobs"][job_name].get("with")
    if with_section:
        sorted_section = {k: with_section[k] for k in sorted(with_section)}
        config["jobs"][job_name]["with"] = sorted_section
    elif with_section is not None:
        del with_section


def __get_coverage_python_version() -> PythonVersion:
    python_version_file = Path(".python-version")
    if python_version_file.exists():
        return python_version_file.read_text().strip()  # ty:ignore[invalid-return-type]
    return DEFAULT_DEV_PYTHON_VERSION


def copy_workflow_file(
    session: Session, /, *, filename: str, repository: str | None = None
) -> None:
    """Install a workflow that is copied verbatim from the policy templates."""
    template_path = COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / filename
    expected_content = template_path.read_text()
    if repository is not None:
        expected_content = resolve_self_references(expected_content, repository)
    if not CONFIG_PATH.pip_constraints.exists():
        expected_content = __remove_constraint_pinning(expected_content)
    workflow_path = CONFIG_PATH.github_workflow_dir / filename
    resource = session.get_path(workflow_path)
    if not resource.exists:
        resource.write_text(expected_content, f"Created {workflow_path} workflow")
        return
    expected_content = preserve_action_versions(expected_content, resource.read_text())
    resource.write_text(expected_content, f"Updated {workflow_path} workflow")


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


def _recommend_vscode_extension(session: Session, /) -> None:
    if not CONFIG_PATH.github_workflow_dir.exists():
        return
    # cspell:ignore cschleiden
    vscode.remove_extension_recommendation(session, "cschleiden.vscode-github-actions")
    vscode.add_extension_recommendation(session, "github.vscode-github-actions")
    ci_workflow = CONFIG_PATH.github_workflow_dir / "ci.yml"
    if ci_workflow.exists():
        action_settings = {
            "github-actions.workflows.pinned.workflows": [str(ci_workflow)],
        }
        vscode.update_settings(session, action_settings)


_USES_PATTERN = re.compile(
    r"^(?P<prefix>[ \t]*(?:-[ \t]+)?uses:[ \t]*)(?P<reference>\S+)(?P<comment>.*)$",
    flags=re.MULTILINE,
)


def preserve_action_versions(expected: str, existing: str) -> str:
    r"""Restore the GitHub Action references that a repository already uses.

    Policy-managed workflows own their structure, but not the versions of the actions
    they call: a downstream repository may pin an action to the immutable commit SHA of
    an exact release, and that pin has to survive the next policy run. Each ``uses:``
    reference in *expected* is therefore replaced by the reference that the same action
    has in *existing* — matched on the action name in front of the ``@``, and by order
    of appearance when one action is used several times.

    >>> expected = "jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v7\n"
    >>> existing = "      - uses: actions/checkout@3d3c42e # v7.0.1\n"
    >>> print(preserve_action_versions(expected, existing), end="")
    jobs:
      build:
        steps:
          - uses: actions/checkout@3d3c42e # v7.0.1

    An action that the repository does not call yet keeps the template version:

    >>> print(preserve_action_versions("  - uses: actions/setup-uv@v7\n", existing))
      - uses: actions/setup-uv@v7
    <BLANKLINE>
    """

    def substitute(match: re.Match) -> str:
        references = available.get(__get_action_name(match["reference"]))
        if not references:
            return match[0]
        return match["prefix"] + references.pop(0)

    available = __collect_action_references(existing)
    return _USES_PATTERN.sub(substitute, expected)


def resolve_self_references(workflow: str, repository: str) -> str:
    r"""Resolve references to the current repository at the workflow commit.

    >>> resolve_self_references(
    ...     "  uses: ComPWA/actions/.github/workflows/ci.yml@v4.0\n",
    ...     "ComPWA/actions",
    ... )
    '  uses: $/.github/workflows/ci.yml\n'
    >>> resolve_self_references(
    ...     "  uses: ComPWA/actions/clean-caches@v4\n",
    ...     "ComPWA/policy",
    ... )
    '  uses: ComPWA/actions/clean-caches@v4\n'
    """

    def substitute(match: re.Match) -> str:
        reference = match["reference"]
        repository_prefix = f"{repository}/"
        if not reference.startswith(repository_prefix):
            return match[0]
        path = reference.removeprefix(repository_prefix).split("@", maxsplit=1)[0]
        return f"{match['prefix']}$/{path}{match['comment']}"

    return _USES_PATTERN.sub(substitute, workflow)


def __collect_action_references(workflow_content: str) -> dict[str, list[str]]:
    references: dict[str, list[str]] = {}
    for match in _USES_PATTERN.finditer(workflow_content):
        name = __get_action_name(match["reference"])
        references.setdefault(name, []).append(match["reference"] + match["comment"])
    return references


def __get_action_name(reference: str) -> str:
    """Strip the version from a ``uses:`` reference.

    >>> __get_action_name("ComPWA/actions/.github/workflows/ci.yml@v4.0")
    'ComPWA/actions/.github/workflows/ci.yml'
    >>> __get_action_name("./.github/actions/local")
    './.github/actions/local'
    """
    return reference.split("@", maxsplit=1)[0]


def remove_workflow(filename: str) -> Changelog:
    path = CONFIG_PATH.github_workflow_dir / filename
    if path.exists():
        path.unlink()
        msg = f"Removed deprecated {filename} workflow"
        return [msg]
    return []


def update_workflow(
    yaml: YAML,
    config: dict,
    path: Path,
    *,
    repository: str | None = None,
) -> Changelog:
    expected_content = __dump_to_string(yaml, config)
    if repository is not None:
        expected_content = resolve_self_references(expected_content, repository)
    if not path.exists():
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(expected_content)
        return [f"Created {path} workflow"]
    existing_content = path.read_text()
    expected_content = preserve_action_versions(expected_content, existing_content)
    if expected_content == existing_content:
        return []
    path.write_text(expected_content)
    return [f"Updated {path} workflow"]


def __dump_to_string(yaml: YAML, config: dict) -> str:
    stream = io.StringIO()
    yaml.dump(config, stream)
    return stream.getvalue()
