"""Check :file:`.github/workflows` folder content."""

from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import tomli
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, LiteralScalarString

from compwa_policy import _to_list
from compwa_policy.characterization import has_documentation, has_notebooks
from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION
from compwa_policy.errors import PolicyError
from compwa_policy.repo.lychee import uses_lychee
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH, vscode
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.pyproject import PythonVersion, has_pyproject_package_name
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap
    from ruamel.yaml.main import YAML

    from compwa_policy import Arguments
    from compwa_policy.config import MacosRunnerLabel, UbuntuRunnerLabel
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.precommit import Precommit
    from compwa_policy.utilities.session import Changelog, Session


_DEFAULT_TASK_RUNNER = "poe"
_MACOS_RUNNER = "macos-15"
_UBUNTU_RUNNER = "ubuntu-24.04"


@check_hook(
    group="github",
    paths=[
        CONFIG_PATH.codecov,
        CONFIG_PATH.precommit,
        CONFIG_PATH.pyproject,
        CONFIG_PATH.pixi_toml,
        CONFIG_PATH.readthedocs,
        "lychee.toml",
        ".lychee.toml",
        ".python-version",
    ],
    directories=(CONFIG_PATH.github_workflow_dir.parent, CONFIG_PATH.pip_constraints),
    enabled=lambda args, _ctx: not args.no_github_actions,
)
def check(session: Session, args: Arguments, ctx: CheckContext) -> None:
    repository = f"{args.repo_organization}/{args.repo_name}"
    keep = args.keep_workflow
    if "cd.yml" not in keep:
        if args.no_cd:
            session.changelog += remove_workflow("cd.yml")
        else:
            _update_cd_workflow(
                session,
                args.no_milestones,
                args.no_pypi,
                args.no_version_branches,
                ubuntu_runner=args.ubuntu_runner,
                repository=repository,
            )
    _update_ci_workflow(
        session,
        keep,
        args.allow_deprecated_workflows,
        ctx.doc_apt_packages,
        ctx.environment_variables,
        args.github_pages,
        args.macos_python_version,
        args.macos_runner,
        args.ubuntu_runner,
        args.dev_python_version,
        args.pytest_single_threaded,
        _to_list(args.ci_skipped_tests),
        repository,
        autofix_ci=args.autofix_ci,
    )
    if args.autofix_ci and "autofix.ci.yml" not in keep:
        _update_autofix_workflow(
            session,
            python_version=args.dev_python_version,
            repository=repository,
        )
    if not args.keep_pr_linting and "pr-linting.yml" not in keep:
        copy_workflow_file(session, filename="pr-linting.yml", repository=repository)
    _recommend_vscode_extension(session)


def _update_cd_workflow(  # ruff: ignore[complex-structure]
    session: Session,
    /,
    no_milestones: bool,
    no_pypi: bool,
    no_version_branches: bool,
    *,
    ubuntu_runner: UbuntuRunnerLabel | None,
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
        if ubuntu_runner and "pypi" in expected_data["jobs"]:
            expected_data["jobs"]["pypi"]["runs-on"] = ubuntu_runner
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
    keep_workflow: set[str],
    /,
    allow_deprecated: bool,
    doc_apt_packages: list[str],
    environment_variables: dict[str, str],
    github_pages: bool,
    macos_python_version: PythonVersion | None,
    macos_runner: MacosRunnerLabel | None,
    ubuntu_runner: UbuntuRunnerLabel | None,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
    repository: str,
    *,
    autofix_ci: bool,
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
            macos_runner,
            ubuntu_runner,
            python_version,
            single_threaded,
            skip_tests,
            autofix_ci=autofix_ci,
        )
        workflow_path = CONFIG_PATH.github_workflow_dir / "ci.yml"
        __update_linkcheck_section(
            expected_data,
            uses_lychee(session),
            doc_apt_packages,
            python_version,
        )
        if not workflow_path.exists():
            if not expected_data.get("jobs"):
                return []
            return update_workflow(
                yaml, expected_data, workflow_path, repository=repository
            )
        existing_data = yaml.load(workflow_path)
        __preserve_custom_jobs(expected_data, existing_data, workflow_path.name)
        if not expected_data.get("jobs"):
            workflow_path.unlink()
            return ["Removed redundant CI workflows"]
        if existing_data != expected_data:
            return update_workflow(
                yaml, expected_data, workflow_path, repository=repository
            )
        return []

    if "ci.yml" not in keep_workflow:
        session.changelog += update()
    if not allow_deprecated:
        session.changelog += _remove_workflows(
            keep_workflow,
            "ci-docs.yml",
            "ci-style.yml",
            "ci-tests.yml",
            "linkcheck.yml",
        )
    if "clean-caches.yml" not in keep_workflow:
        copy_workflow_file(session, filename="clean-caches.yml", repository=repository)
    session.changelog += _remove_workflows(keep_workflow, "clean-cache.yml")


def __preserve_custom_jobs(expected: dict, existing: dict, filename: str) -> None:
    """Add jobs from the existing workflow that the policy template does not define."""
    yaml = create_prettier_round_trip_yaml()
    template = yaml.load(COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / filename)
    for name, job_def in existing.get("jobs", {}).items():
        if name not in template["jobs"]:
            expected["jobs"][name] = job_def


def _get_ci_workflow(  # ruff: ignore[too-many-positional-arguments]
    path: Path,
    precommit: Precommit,
    doc_apt_packages: list[str],
    environment_variables: dict[str, str],
    github_pages: bool,
    macos_python_version: PythonVersion | None,
    macos_runner: MacosRunnerLabel | None,
    ubuntu_runner: UbuntuRunnerLabel | None,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
    *,
    autofix_ci: bool = False,
) -> tuple[YAML, dict]:
    yaml = create_prettier_round_trip_yaml()
    config = yaml.load(path)
    __update_env_section(config, environment_variables)
    __update_doc_section(config, doc_apt_packages, python_version, github_pages)
    __update_pytest_section(
        config,
        macos_python_version,
        python_version,
        single_threaded,
        skip_tests,
        macos_runner=macos_runner,
        ubuntu_runner=ubuntu_runner,
    )
    __update_style_section(config, python_version, precommit, autofix_ci=autofix_ci)
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
        task_runner = __get_task_runner()
        if task_runner != _DEFAULT_TASK_RUNNER:
            with_section["task-runner"] = task_runner
        if with_section:
            config["jobs"]["doc"]["with"] = with_section
        __update_with_section(config, job_name="doc")
    else:
        del config["jobs"]["doc"]


def __update_style_section(
    config: CommentedMap,
    python_version: PythonVersion,
    precommit: Precommit,
    *,
    autofix_ci: bool,
) -> None:
    if __is_remove_style_job(precommit):
        del config["jobs"]["style"]
        return
    if autofix_ci:
        config["jobs"]["style"].pop("secrets", None)
    with_section: dict[str, Any] = {}
    if autofix_ci or (CONFIG_PATH.github_workflow_dir / "autofix.ci.yml").exists():
        with_section["autofix-ci"] = True
    precommit_ci = precommit.document.get("ci")
    if precommit_ci is not None:
        hooks = precommit_ci.get("skip", [])
        with_section["hooks"] = DoubleQuotedScalarString(" ".join(hooks))
    if has_notebooks():
        with_section["notebooks"] = True
    if python_version != DEFAULT_DEV_PYTHON_VERSION:
        with_section["python-version"] = DoubleQuotedScalarString(python_version)
    if with_section:
        config["jobs"]["style"]["with"] = with_section


def _update_autofix_workflow(
    session: Session,
    /,
    *,
    python_version: PythonVersion,
    repository: str,
) -> None:
    """Let the autofix.ci GitHub App commit fixes instead of a personal access token.

    The app takes over the automatic fix commits of pre-commit.ci, so that both do not
    push the same fixes to a PR.
    """
    yaml = create_prettier_round_trip_yaml()
    template = COMPWA_POLICY_DIR / CONFIG_PATH.github_workflow_dir / "autofix.ci.yml"
    config = yaml.load(template)
    if python_version != DEFAULT_DEV_PYTHON_VERSION:
        config["jobs"]["autofix"]["with"] = {
            "python-version": DoubleQuotedScalarString(python_version)
        }
    workflow_path = CONFIG_PATH.github_workflow_dir / "autofix.ci.yml"
    session.changelog += update_workflow(
        yaml, config, workflow_path, repository=repository
    )
    precommit_ci = session.precommit.document.get("ci")
    if precommit_ci is not None and precommit_ci.get("autofix_prs") is not False:
        precommit_ci["autofix_prs"] = False
        session.precommit.changelog.append(
            "Set ci.autofix_prs to false, because autofix.ci commits the fixes"
        )


def __is_remove_style_job(precommit: Precommit) -> bool:
    precommit_ci = precommit.document.get("ci")
    outsource_to_precommit = precommit_ci is not None and "skip" not in precommit_ci
    repository_has_notebooks = has_notebooks()
    return outsource_to_precommit and not repository_has_notebooks


def __update_pytest_section(
    config: CommentedMap,
    macos_python_version: PythonVersion | None,
    python_version: PythonVersion,
    single_threaded: bool,
    skip_tests: list[str],
    *,
    macos_runner: MacosRunnerLabel | None,
    ubuntu_runner: UbuntuRunnerLabel | None,
) -> None:
    test_dir = "tests"
    if not os.path.exists(test_dir):
        del config["jobs"]["test"]
    else:
        coverage_python_version = None
        if CONFIG_PATH.codecov.exists():
            coverage_python_version = __get_coverage_python_version()
        matrix = _create_test_matrix(
            __get_supported_python_versions(python_version),
            coverage_python_version,
            macos_python_version,
            skip_tests,
            macos_runner=macos_runner,
            ubuntu_runner=ubuntu_runner,
        )
        if not matrix:
            del config["jobs"]["test"]
            return
        with_section: dict[str, Any] = {
            "matrix": LiteralScalarString(json.dumps(matrix, indent=2) + "\n")
        }
        task_runner = __get_task_runner()
        if task_runner not in {_DEFAULT_TASK_RUNNER, "none"}:
            with_section["task-runner"] = task_runner
        if single_threaded:
            with_section["multithreaded"] = False
        output_path = f"{test_dir}/output/"
        if os.path.exists(output_path):
            with_section["test-output-path"] = output_path
        if with_section:
            config["jobs"]["test"]["with"] = with_section
        __update_with_section(config, job_name="test")


def __update_linkcheck_section(
    config: dict,
    has_lychee: bool,
    apt_packages: list[str],
    python_version: PythonVersion,
) -> None:
    """Call the workflow that fits the link checker of the repository, if any."""
    if has_lychee:
        return
    if not __runs_sphinx_linkcheck():
        del config["jobs"]["linkcheck"]
        return
    job = config["jobs"]["linkcheck"]
    job["uses"] = job["uses"].replace("ci-linkcheck.yml", "linkcheck.yml")
    with_section: dict[str, Any] = {}
    if apt_packages:
        with_section["apt-packages"] = " ".join(apt_packages)
    if python_version != DEFAULT_DEV_PYTHON_VERSION:
        with_section["python-version"] = DoubleQuotedScalarString(python_version)
    task_runner = __get_task_runner()
    if task_runner != _DEFAULT_TASK_RUNNER:
        with_section["task-runner"] = task_runner
    if with_section:
        job["with"] = with_section


def __runs_sphinx_linkcheck() -> bool:
    tool = __load_toml(CONFIG_PATH.pyproject).get("tool", {})
    poe = tool.get("poe", {})
    pixi = tool.get("pixi", {}) or __load_toml(CONFIG_PATH.pixi_toml)
    task_tables = [
        poe.get("tasks", {}),
        *(group.get("tasks", {}) for group in poe.get("groups", {}).values()),
        pixi.get("tasks", {}),
        *(feature.get("tasks", {}) for feature in pixi.get("feature", {}).values()),
    ]
    tasks = [table["linkcheck"] for table in task_tables if "linkcheck" in table]
    return any("sphinx" in str(task) for task in tasks)


def __get_task_runner() -> str:
    tool = __load_toml(CONFIG_PATH.pyproject).get("tool", {})
    if tool.get("poe", {}).get("tasks"):
        return "poe"
    if tool.get("pixi", {}).get("tasks"):
        return "pixi"
    if __load_toml(CONFIG_PATH.pixi_toml).get("tasks"):
        return "pixi"
    return "none"


def __load_toml(path: Path | str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as stream:
        return tomli.load(stream)


def __get_supported_python_versions(fallback: PythonVersion) -> list[str]:
    project = __load_toml(CONFIG_PATH.pyproject).get("project", {})
    prefix = "Programming Language :: Python :: "
    versions = [
        classifier.removeprefix(prefix)
        for classifier in project.get("classifiers", [])
        if classifier.startswith(f"{prefix}3.")
    ]
    if versions:
        return versions
    requires_python = project.get("requires-python")
    if requires_python is None:
        return [fallback]
    return _get_allowed_python_versions(requires_python)


def _get_allowed_python_versions(version_range: str) -> list[str]:
    """Get the Python versions that a version range specifier allows.

    >>> _get_allowed_python_versions(">=3.9,<3.13")
    ['3.9', '3.10', '3.11', '3.12']
    """
    specifier = SpecifierSet(version_range)
    versions = [f"3.{minor}" for minor in range(6, 15)]
    return [version for version in versions if Version(version) in specifier]


def _create_test_matrix(
    supported_versions: list[str],
    coverage_python_version: str | None,
    macos_python_version: str | None,
    skip_tests: list[str],
    *,
    macos_runner: MacosRunnerLabel | None = None,
    ubuntu_runner: UbuntuRunnerLabel | None = None,
) -> dict[str, Any]:
    """Create the job matrix of the test workflow.

    >>> _create_test_matrix(["3.11", "3.12", "3.13"], "3.12", "3.11", ["3.13"])
    ... # doctest: +NORMALIZE_WHITESPACE
    {'python-version': ['3.11'], 'runs-on': ['ubuntu-24.04'],
     'include': [{'codecov': 'codecov', 'python-version': '3.12', 'runs-on': 'ubuntu-24.04'},
                 {'python-version': '3.11', 'runs-on': 'macos-15'}]}
    >>> _create_test_matrix(["3.11"], None, None, ["all"])
    {}
    """
    for version in filter(None, [coverage_python_version, macos_python_version]):
        if version not in supported_versions:
            supported = ", ".join(supported_versions)
            msg = f"Selected Python {version} for CI, but the package only supports Python {supported}"
            raise PolicyError(msg)
    if "all" in skip_tests:
        versions = []
    else:
        excluded = {*skip_tests, coverage_python_version}
        versions = sorted(
            (v for v in supported_versions if v not in excluded), key=Version
        )
    matrix: dict[str, Any] = {}
    if versions:
        matrix = {
            "python-version": versions,
            "runs-on": [ubuntu_runner or _UBUNTU_RUNNER],
        }
    includes: list[dict[str, str]] = []
    if coverage_python_version:
        includes.append({
            "codecov": "codecov",
            "python-version": coverage_python_version,
            "runs-on": ubuntu_runner or _UBUNTU_RUNNER,
        })
    if macos_python_version:
        includes.append({
            "python-version": macos_python_version,
            "runs-on": macos_runner or _MACOS_RUNNER,
        })
    if includes:
        matrix["include"] = includes
    return matrix


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
    vscode.add_extension_recommendation(session, "github.vscode-pull-request-github")
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

    >>> preserve_action_versions("  - uses: actions/setup-uv@v7\n", existing)
    '  - uses: actions/setup-uv@v7\n'
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


def _remove_workflows(keep_workflow: set[str], *filenames: str) -> Changelog:
    changelog: Changelog = []
    for filename in filenames:
        if filename not in keep_workflow:
            changelog += remove_workflow(filename)
    return changelog


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
