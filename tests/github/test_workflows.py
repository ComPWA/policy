import io
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from compwa_policy.github.workflows import (
    check,
    preserve_action_versions,
    remove_workflow,
)
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.pyproject import PythonVersion
from compwa_policy.utilities.session import Session

_WORKFLOW_DIR = Path(".github/workflows")


def _precommit(content: str = "repos: []\n") -> ModifiablePrecommit:
    return ModifiablePrecommit.load(io.StringIO(content))


@pytest.fixture
def workflows_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_init: Callable[[Path], None],
    git_add: Callable[[Path], None],
) -> Path:
    git_init(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "conf.py").touch()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-package"\nrequires-python = ">=3.10"\n'
    )
    git_add(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run_main(
    run_check,
    *,
    doc_apt_packages: list[str] | None = None,
    environment_variables: dict[str, str] | None = None,
    github_pages: bool = False,
    macos_python_version: PythonVersion | None = None,
    no_cd: bool = False,
    no_milestones: bool = False,
    no_pypi: bool = False,
    no_version_branches: bool = False,
    precommit_content: str = "repos: []\n",
    python_version: PythonVersion = "3.13",
    single_threaded: bool = False,
    skip_tests: list[str] | None = None,
) -> list[str]:
    with Session.load(_precommit(precommit_content)) as session:
        run_check(
            check,
            session,
            allow_deprecated_workflows=False,
            doc_apt_packages=doc_apt_packages or [],
            environment_variables=environment_variables or {},
            github_pages=github_pages,
            keep_pr_linting=False,
            macos_python_version=macos_python_version,
            no_cd=no_cd,
            no_milestones=no_milestones,
            no_pypi=no_pypi,
            no_version_branches=no_version_branches,
            dev_python_version=python_version,
            pytest_single_threaded=single_threaded,
            ci_skipped_tests=",".join(skip_tests or []),
        )
        return session.collect_changes()


def describe_main():
    def creates_workflows(workflows_repo: Path, run_check):
        changes = _run_main(run_check)
        assert changes
        assert (workflows_repo / _WORKFLOW_DIR / "cd.yml").exists()
        assert (workflows_repo / _WORKFLOW_DIR / "ci.yml").exists()
        assert (workflows_repo / _WORKFLOW_DIR / "pr-linting.yml").exists()
        assert (workflows_repo / _WORKFLOW_DIR / "clean-caches.yml").exists()

    def applies_options(workflows_repo: Path, run_check):
        changes = _run_main(
            run_check,
            doc_apt_packages=["graphviz"],
            environment_variables={"PYTHONHASHSEED": "0"},
            github_pages=True,
            macos_python_version="3.12",
            python_version="3.12",
            single_threaded=True,
            skip_tests=["3.10"],
        )
        assert changes
        ci = (workflows_repo / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "graphviz" in ci
        assert "PYTHONHASHSEED" in ci

    def skips_cd_workflow(workflows_repo: Path, run_check):
        changes = _run_main(run_check, no_cd=True)
        assert changes
        assert not (workflows_repo / _WORKFLOW_DIR / "cd.yml").exists()

    def bans_cd_jobs(workflows_repo: Path, run_check):
        _run_main(run_check, no_pypi=True, no_milestones=True, no_version_branches=True)
        cd_path = workflows_repo / _WORKFLOW_DIR / "cd.yml"
        if cd_path.exists():
            assert "pypi" not in cd_path.read_text()

    def configures_codecov(workflows_repo: Path, run_check):
        (workflows_repo / "codecov.yml").touch()
        (workflows_repo / ".python-version").write_text("3.11\n")
        changes = _run_main(run_check)
        assert changes
        ci = (workflows_repo / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "CODECOV_TOKEN" in ci
        assert "3.11" in ci  # coverage python version from .python-version

    def removes_style_job_when_outsourced(workflows_repo: Path, run_check):
        precommit = "ci:\n  autofix_prs: true\nrepos: []\n"
        changes = _run_main(run_check, precommit_content=precommit)
        assert changes
        ci = (workflows_repo / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "style:" not in ci  # style job outsourced to pre-commit.ci

    def removes_doc_and_test_jobs(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
        run_check,
    ):
        git_init(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-package"\n')
        git_add(tmp_path)
        monkeypatch.chdir(tmp_path)
        changes = _run_main(run_check)
        assert changes
        ci = (tmp_path / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "doc:" not in ci  # no documentation -> doc job removed
        assert "test:" not in ci  # no tests directory -> test job removed


def describe_remove_workflow():
    def is_noop_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        assert not remove_workflow("ci-tests.yml")  # nothing to remove

    def removes_present_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        workflow = tmp_path / _WORKFLOW_DIR / "ci-tests.yml"
        workflow.parent.mkdir(parents=True)
        workflow.touch()
        changes = remove_workflow("ci-tests.yml")
        assert any("Removed deprecated ci-tests.yml" in m for m in changes)
        assert not workflow.exists()


def describe_preserve_action_versions():
    @pytest.mark.parametrize(
        ("expected", "existing", "output"),
        [
            (
                "  - uses: actions/checkout@v7\n  - uses: actions/checkout@v7\n",
                "  - uses: actions/checkout@sha1 # v7.0.1\n",
                "  - uses: actions/checkout@sha1 # v7.0.1\n  - uses: actions/checkout@v7\n",
            ),
            (
                "  - uses: actions/checkout@v7\n",
                "  - uses: ./.github/actions/local\n",
                "  - uses: actions/checkout@v7\n",
            ),
            (
                "jobs:\n  lock:\n    uses: ComPWA/actions/.github/workflows/lock.yml@v4\n",
                "jobs:\n  lock:\n    uses: ComPWA/actions/.github/workflows/lock.yml@sha2\n",
                "jobs:\n  lock:\n    uses: ComPWA/actions/.github/workflows/lock.yml@sha2\n",
            ),
        ],
        ids=["repeated-action", "unknown-action", "reusable-workflow"],
    )
    def substitutes_references(expected: str, existing: str, output: str):
        assert preserve_action_versions(expected, existing) == output


def describe_action_pins():
    def survive_a_rerun(workflows_repo: Path, run_check):
        _run_main(run_check)
        pinned = {}
        for filename in ("cd.yml", "ci.yml", "clean-caches.yml", "pr-linting.yml"):
            path = workflows_repo / _WORKFLOW_DIR / filename
            pinned[filename] = re.sub(
                r"@[^\s#]+", "@0123456789abcdef # pinned", path.read_text()
            )
            path.write_text(pinned[filename])
        changes = _run_main(run_check)
        assert not changes  # pins alone must not trigger an update
        for filename, content in pinned.items():
            assert (workflows_repo / _WORKFLOW_DIR / filename).read_text() == content
