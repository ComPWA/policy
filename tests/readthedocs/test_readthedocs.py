from __future__ import annotations

import io
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION
from compwa_policy.errors import PrecommitError
from compwa_policy.repo import readthedocs

if TYPE_CHECKING:
    from compwa_policy.utilities.pyproject.getters import PythonVersion

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


def describe_main():
    def updates_extend_style_config():
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
        input_stream = io.StringIO(bad_config)
        with pytest.raises(PrecommitError) as exception:
            readthedocs.main(
                "conda",
                python_version=DEFAULT_DEV_PYTHON_VERSION,
                source=input_stream,
            )
        assert str(exception.value).strip() == _expected_message(
            DEFAULT_DEV_PYTHON_VERSION
        )

        input_stream.seek(0)
        assert input_stream.read().strip() == _good_extend().strip()

    @pytest.mark.parametrize(
        "good_config",
        [_good_extend(), _good_overwrite(DEFAULT_DEV_PYTHON_VERSION)],
        ids=["extend", "overwrite"],
    )
    def leaves_good_config_unchanged(good_config: str):
        input_stream = io.StringIO(good_config)
        readthedocs.main(
            "conda",
            python_version=DEFAULT_DEV_PYTHON_VERSION,
            source=input_stream,
        )
        input_stream.seek(0)
        assert input_stream.read().strip() == good_config.strip()

    @pytest.mark.parametrize(
        "bad_config",
        [BAD_OVERWRITE_WITH_JOBS, BAD_OVERWRITE_WITHOUT_JOBS],
        ids=["with-jobs", "without-jobs"],
    )
    @pytest.mark.parametrize("python_version", ["3.9", "3.10"])
    def overwrites_bad_config(python_version: PythonVersion, bad_config: str):
        input_stream = io.StringIO(bad_config)
        with pytest.raises(PrecommitError) as exception:
            readthedocs.main("conda", python_version, source=input_stream)
        assert str(exception.value).strip() == _expected_message(python_version)

        input_stream.seek(0)
        assert input_stream.read().strip() == _good_overwrite(python_version).strip()
