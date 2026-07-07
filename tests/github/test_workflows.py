import io
from collections.abc import Callable
from pathlib import Path

import pytest

from compwa_policy.errors import PrecommitError
from compwa_policy.github.workflows import main, remove_workflow
from compwa_policy.utilities.precommit import Precommit
from compwa_policy.utilities.pyproject import PythonVersion

_WORKFLOW_DIR = Path(".github/workflows")


def _precommit(content: str = "repos: []\n") -> Precommit:
    return Precommit.load(io.StringIO(content))


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
) -> None:
    main(
        _precommit(precommit_content),
        allow_deprecated=False,
        doc_apt_packages=doc_apt_packages or [],
        environment_variables=environment_variables or {},
        github_pages=github_pages,
        keep_pr_linting=False,
        macos_python_version=macos_python_version,
        no_cd=no_cd,
        no_milestones=no_milestones,
        no_pypi=no_pypi,
        no_version_branches=no_version_branches,
        python_version=python_version,
        single_threaded=single_threaded,
        skip_tests=skip_tests or [],
    )


def describe_main():
    def creates_workflows(workflows_repo: Path):
        with pytest.raises(PrecommitError):
            _run_main()

        assert (workflows_repo / _WORKFLOW_DIR / "cd.yml").exists()
        assert (workflows_repo / _WORKFLOW_DIR / "ci.yml").exists()
        assert (workflows_repo / _WORKFLOW_DIR / "pr-linting.yml").exists()
        assert (workflows_repo / _WORKFLOW_DIR / "clean-caches.yml").exists()

    def applies_options(workflows_repo: Path):
        with pytest.raises(PrecommitError):
            _run_main(
                doc_apt_packages=["graphviz"],
                environment_variables={"PYTHONHASHSEED": "0"},
                github_pages=True,
                macos_python_version="3.12",
                python_version="3.12",
                single_threaded=True,
                skip_tests=["3.10"],
            )

        ci = (workflows_repo / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "graphviz" in ci
        assert "PYTHONHASHSEED" in ci

    def skips_cd_workflow(workflows_repo: Path):
        with pytest.raises(PrecommitError):
            _run_main(no_cd=True)
        assert not (workflows_repo / _WORKFLOW_DIR / "cd.yml").exists()

    def bans_cd_jobs(workflows_repo: Path):
        with pytest.raises(PrecommitError):
            _run_main(no_pypi=True, no_milestones=True, no_version_branches=True)
        cd_path = workflows_repo / _WORKFLOW_DIR / "cd.yml"
        if cd_path.exists():
            assert "pypi" not in cd_path.read_text()

    def configures_codecov(workflows_repo: Path):
        (workflows_repo / "codecov.yml").touch()
        (workflows_repo / ".python-version").write_text("3.11\n")
        with pytest.raises(PrecommitError):
            _run_main()
        ci = (workflows_repo / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "CODECOV_TOKEN" in ci
        assert "3.11" in ci  # coverage python version from .python-version

    def removes_style_job_when_outsourced(workflows_repo: Path):
        precommit = "ci:\n  autofix_prs: true\nrepos: []\n"
        with pytest.raises(PrecommitError):
            _run_main(precommit_content=precommit)
        ci = (workflows_repo / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "style:" not in ci  # style job outsourced to pre-commit.ci

    def removes_doc_and_test_jobs(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init: Callable[[Path], None],
        git_add: Callable[[Path], None],
    ):
        git_init(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-package"\n')
        git_add(tmp_path)
        monkeypatch.chdir(tmp_path)
        with pytest.raises(PrecommitError):
            _run_main()
        ci = (tmp_path / _WORKFLOW_DIR / "ci.yml").read_text()
        assert "doc:" not in ci  # no documentation -> doc job removed
        assert "test:" not in ci  # no tests directory -> test job removed


def describe_remove_workflow():
    def is_noop_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        remove_workflow("ci-tests.yml")  # nothing to remove

    def removes_present_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        workflow = tmp_path / _WORKFLOW_DIR / "ci-tests.yml"
        workflow.parent.mkdir(parents=True)
        workflow.touch()
        with pytest.raises(PrecommitError, match=r"Removed deprecated ci-tests.yml"):
            remove_workflow("ci-tests.yml")
        assert not workflow.exists()
