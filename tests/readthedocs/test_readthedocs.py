from __future__ import annotations

import subprocess  # noqa: S404
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION
from compwa_policy.repo import readthedocs
from compwa_policy.utilities.session import Session

if TYPE_CHECKING:
    from pathlib import Path

    from compwa_policy.utilities.pyproject.getters import PythonVersion


def _main(*args, **kwargs) -> list[str]:
    with Session() as session:
        readthedocs.main(session, *args, **kwargs)
        return session.collect_changes()


BAD_OVERWRITE_WITH_JOBS = dedent("""
    version: 2
    build:
      os: ubuntu-20.04
      tools:
        python: "3.7"
      jobs:
        post_install:
          - pip install -e .[doc]
    sphinx:
      configuration: docs/conf.py
""").lstrip()

BAD_OVERWRITE_WITHOUT_JOBS = dedent("""
    version: 2
    build:
      os: ubuntu-20.04
      tools:
        python: "3.7"
    sphinx:
      configuration: docs/conf.py
""").lstrip()


def _good_extend() -> str:
    return dedent(f"""
        version: 2
        build:
          os: ubuntu-24.04
          tools:
            python: "{DEFAULT_DEV_PYTHON_VERSION}"
          jobs:
            post_install:
              - python -m pip install 'uv>=0.2.0'
              - python -m uv pip install -e .[doc]
              - |
                wget https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.2-linux-x86_64.tar.gz
              - tar xzf julia-1.9.2-linux-x86_64.tar.gz
              - mkdir bin
              - ln -s $PWD/julia-1.9.2/bin/julia bin/julia
              - ./bin/julia docs/InstallIJulia.jl
        sphinx:
          configuration: docs/conf.py
    """).lstrip()


def _good_overwrite(python_version: str) -> str:
    return dedent(f"""
        version: 2
        build:
          os: ubuntu-24.04
          tools:
            python: "{python_version}"
          jobs:
            post_install:
              - python -m pip install 'uv>=0.2.0'
              - python -m uv pip install -e .[doc]
        sphinx:
          configuration: docs/conf.py
    """).lstrip()


def _expected_message(python_version: str) -> str:
    return dedent(f"""
      Updated .readthedocs.yml:
        - Set build.os to ubuntu-24.04
        - Set build.tools.python to {python_version!r}
        - Updated pip install steps
    """).strip()


def _write_rtd(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".readthedocs.yml"
    path.write_text(content)
    return path


def describe_main():
    def updates_extend_style_config(tmp_path: Path):
        bad_config = dedent("""
            version: 2
            build:
              os: ubuntu-20.04
              tools:
                python: "3.10"
              jobs:
                post_install:
                  - pip install -e .[doc]
                  - |
                    wget https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.2-linux-x86_64.tar.gz
                  - tar xzf julia-1.9.2-linux-x86_64.tar.gz
                  - mkdir bin
                  - ln -s $PWD/julia-1.9.2/bin/julia bin/julia
                  - ./bin/julia docs/InstallIJulia.jl
            sphinx:
              configuration: docs/conf.py
        """).lstrip()
        config = _write_rtd(tmp_path, bad_config)
        changes = _main(
            "conda",
            python_version=DEFAULT_DEV_PYTHON_VERSION,
            source=config,
        )
        assert changes
        assert changes[0].strip() == _expected_message(DEFAULT_DEV_PYTHON_VERSION)
        assert config.read_text().strip() == _good_extend().strip()

    @pytest.mark.parametrize(
        "good_config",
        [_good_extend(), _good_overwrite(DEFAULT_DEV_PYTHON_VERSION)],
        ids=["extend", "overwrite"],
    )
    def leaves_good_config_unchanged(good_config: str, tmp_path: Path):
        config = _write_rtd(tmp_path, good_config)
        _main(
            "conda",
            python_version=DEFAULT_DEV_PYTHON_VERSION,
            source=config,
        )
        assert config.read_text().strip() == good_config.strip()

    @pytest.mark.parametrize(
        "bad_config",
        [BAD_OVERWRITE_WITH_JOBS, BAD_OVERWRITE_WITHOUT_JOBS],
        ids=["with-jobs", "without-jobs"],
    )
    @pytest.mark.parametrize("python_version", ["3.9", "3.10"])
    def overwrites_bad_config(
        python_version: PythonVersion, bad_config: str, tmp_path: Path
    ):
        config = _write_rtd(tmp_path, bad_config)
        changes = _main("conda", python_version, source=config)
        assert changes
        assert changes[0].strip() == _expected_message(python_version)
        assert config.read_text().strip() == _good_overwrite(python_version).strip()

    def returns_early_when_config_missing(tmp_path: Path):
        _main(
            "uv",
            python_version=DEFAULT_DEV_PYTHON_VERSION,
            source=tmp_path / ".readthedocs.yml",
        )

    def configures_uv_build(rtd_repo: Path):
        (rtd_repo / "pyproject.toml").write_text(
            '[project]\nname = "x"\n\n[dependency-groups]\ndoc = ["poethepoet"]\n'
        )
        _write_rtd(
            rtd_repo,
            dedent("""
            version: 2
            build:
              os: ubuntu-24.04
              apt_packages:
                - graphviz
              tools:
                python: "3.12"
              jobs:
                post_install:
                  - pip install -e .[doc]
            sphinx:
              configuration: docs/conf.py
            """).lstrip(),
        )
        changes = _main("uv", python_version="3.12")
        assert changes  # something changed
        result = (rtd_repo / ".readthedocs.yml").read_text()
        assert "pixi global install graphviz uv" in result
        assert "uvx --from poethepoet poe doc" in result
        assert "apt_packages" not in result

    def configures_pixi_build_with_poe(rtd_repo: Path):
        (rtd_repo / "pyproject.toml").write_text(
            '[project]\nname = "x"\n\n[dependency-groups]\ndoc = ["poethepoet"]\n'
        )
        _write_rtd(
            rtd_repo,
            dedent("""
            version: 2
            build:
              os: ubuntu-24.04
              tools:
                python: "3.12"
            sphinx:
              configuration: docs/conf.py
            """).lstrip(),
        )
        changes = _main("pixi+uv", python_version="3.12")
        assert changes  # something changed
        result = (rtd_repo / ".readthedocs.yml").read_text()
        assert "pixi run poe doc" in result

    def sets_sphinx_configuration_when_missing(rtd_repo: Path):
        (rtd_repo / "pyproject.toml").write_text('[project]\nname = "x"\n')
        _write_rtd(
            rtd_repo,
            dedent("""
            version: 2
            build:
              os: ubuntu-24.04
              tools:
                python: "3.12"
            """).lstrip(),
        )
        changes = _main("conda", python_version="3.12")
        assert any("Set sphinx.configuration" in m for m in changes)
        result = (rtd_repo / ".readthedocs.yml").read_text()
        assert "configuration: docs/conf.py" in result

    def reuses_existing_pixi_packages(rtd_repo: Path):
        (rtd_repo / "pyproject.toml").write_text('[project]\nname = "x"\n')
        _write_rtd(
            rtd_repo,
            dedent("""
            version: 2
            build:
              os: ubuntu-24.04
              tools:
                python: "3.12"
              commands:
                - |
                  export PIXI_HOME=$READTHEDOCS_VIRTUALENV_PATH
                  curl -fsSL https://pixi.sh/install.sh | bash
                  pixi global install graphviz julia
            sphinx:
              configuration: docs/conf.py
            """).lstrip(),
        )
        changes = _main("uv", python_version="3.12")
        assert changes  # something changed
        result = (rtd_repo / ".readthedocs.yml").read_text()
        assert "pixi global install graphviz julia uv" in result

    def configures_pixi_build_without_poe(rtd_repo: Path):
        (rtd_repo / "pyproject.toml").write_text('[project]\nname = "x"\n')
        _write_rtd(
            rtd_repo,
            dedent("""
            version: 2
            build:
              os: ubuntu-24.04
              tools:
                python: "3.12"
            sphinx:
              configuration: docs/conf.py
            """).lstrip(),
        )
        changes = _main("pixi+uv", python_version="3.12")
        assert changes  # something changed
        result = (rtd_repo / ".readthedocs.yml").read_text()
        assert "pixi run doc" in result


@pytest.fixture
def rtd_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "conf.py").touch()
    monkeypatch.chdir(tmp_path)
    return tmp_path
