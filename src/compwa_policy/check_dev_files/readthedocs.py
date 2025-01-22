"""Update Read the Docs configuration."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent, indent
from typing import IO, TYPE_CHECKING, Callable, cast

from ruamel.yaml.scalarstring import DoubleQuotedScalarString, LiteralScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, get_nested_dict
from compwa_policy.utilities.match import filter_files, git_ls_files
from compwa_policy.utilities.pyproject import get_constraints_file
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap

    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.utilities.pyproject.getters import PythonVersion


def main(
    package_manager: PackageManagerChoice,
    python_version: PythonVersion,
    source: IO | Path | str = CONFIG_PATH.readthedocs,
) -> None:
    if isinstance(source, str):
        source = Path(source)
    if isinstance(source, Path) and not source.exists():
        return
    rtd = ReadTheDocs(source)
    _set_sphinx_configuration(rtd)
    _update_os(rtd)
    _update_python_version(rtd, python_version)
    if package_manager == "pixi+uv":
        _remove_redundant_settings(rtd)
        _update_build_step_for_pixi(rtd)
    elif package_manager == "uv":
        apt_packages = set(rtd.document.get("build", {}).get("apt_packages", []))
        pixi_packages = apt_packages & {"graphviz"}
        pixi_packages |= _get_existing_pixi_packages(rtd)
        if "uv" in package_manager:
            pixi_packages.add("uv")
        _install_pixi(rtd, pixi_packages)
        _remove_redundant_settings(rtd)
        _update_build_step_for_uv(rtd)
    else:
        _update_post_install(rtd, python_version, package_manager)
    rtd.finalize()


def _set_sphinx_configuration(config: ReadTheDocs) -> None:
    if "sphinx" not in config.document:
        config.document["sphinx"] = {}
    sphinx = config.document["sphinx"]
    if "configuration" not in sphinx:
        conf_path = __get_sphinx_config_path()
        sphinx["configuration"] = str(conf_path)
        msg = f"Set sphinx.configuration to {conf_path}"
        config.changelog.append(msg)


def __get_sphinx_config_path() -> Path | None:
    conf_path = Path("docs/conf.py")
    if conf_path.exists():
        return conf_path
    candidate_paths = list(filter_files(["**/conf.py"]))
    if not candidate_paths:
        return None
    return Path(candidate_paths[0])


def _update_os(config: ReadTheDocs) -> None:
    build = cast("CommentedMap", config.document.get("build"))
    if build is None:
        return
    os: str | None = build.get("os")
    expected_os = "ubuntu-24.04"
    if os == expected_os:
        return
    build["os"] = expected_os
    msg = f"Set build.os to {expected_os}"
    config.changelog.append(msg)


def _update_python_version(config: ReadTheDocs, python_version: PythonVersion) -> None:
    tools = cast("CommentedMap", config.document.get("build", {}).get("tools"))
    if tools is None:
        return
    existing_version: str | None = tools.get("python")
    if existing_version is None:
        return
    expected_version = DoubleQuotedScalarString(python_version)
    if expected_version == existing_version:
        return
    tools["python"] = expected_version
    msg = f"Set build.tools.python to {python_version!r}"
    config.changelog.append(msg)


def _get_existing_pixi_packages(config: ReadTheDocs) -> set[str]:
    commands = __get_commands(config, create=False)
    for cmd in commands:
        packages = __get_pixi_packages(cmd)
        if packages is not None:
            return set(packages)
    return set()


def __get_pixi_packages(cmd: str) -> list[str] | None:
    '''Get the set of Pixi packages already installed.

    >>> __get_pixi_packages("""
    ...     export PIXI_HOME=$READTHEDOCS_VIRTUALENV_PATH
    ...     curl -fsSL https://pixi.sh/install.sh | bash
    ...     pixi global install graphviz uv
    ... """)
    ['graphviz', 'uv']
    '''
    if "pixi global install" not in cmd:
        return None
    for sub_cmd in cmd.split("\n"):
        match = re.match(r"pixi global install (.*)", sub_cmd.strip())
        if match:
            return match.group(1).split()
    return None


def _install_pixi(config: ReadTheDocs, packages: set[str]) -> None:
    pixi_cmd = __get_pixi_install_statement()
    if packages:
        pixi_cmd += f"\npixi global install {' '.join(sorted(packages))}"
    commands = __get_commands(config)
    idx: int | None = None
    for i, cmd in enumerate(commands):
        if "pixi" in cmd:
            idx = i
            break
    if idx is None:
        commands.insert(0, LiteralScalarString(pixi_cmd))
    elif commands[idx] != pixi_cmd:
        commands[idx] = LiteralScalarString(pixi_cmd)
    else:
        return
    msg = "Updated Pixi installation in Read the Docs"
    config.changelog.append(msg)


def __get_pixi_install_statement() -> str:
    return dedent("""
        export PIXI_HOME=$READTHEDOCS_VIRTUALENV_PATH
        curl -fsSL https://pixi.sh/install.sh | bash
    """).strip()


def __get_commands(config: ReadTheDocs, create: bool = True) -> list[str]:
    if not create:
        return config.document.get("build", {}).get("commands", [])
    if "build" not in config.document:
        config.document["build"] = {}
    build = config.document["build"]
    if "commands" not in build:
        build["commands"] = []
    return build["commands"]


def _remove_redundant_settings(config: ReadTheDocs) -> None:
    redundant_keys = [
        "build.apt_packages",
        "build.jobs",
        "formats",
    ]
    removed_keys = [
        key for key in redundant_keys if __remove_nested_key(config.document, key)
    ]
    if removed_keys:
        msg = f"Removed redundant keys from Read the Docs configuration: {', '.join(removed_keys)}"
        config.changelog.append(msg)


def __remove_nested_key(dct: dict, dotted_key: str) -> bool:
    keys = dotted_key.split(".")
    for key in keys[:-1]:
        if key not in dct:
            return False
        dct = dct[key]
    key = keys[-1]
    if key not in dct:
        return False
    del dct[key]
    return True


def _update_build_step_for_pixi(config: ReadTheDocs) -> None:
    new_command = __get_pixi_install_statement() + "\n"
    new_command += dedent(R"""
        export UV_LINK_MODE=copy
        pixi run \
          uv run \
            --group doc \
            --no-dev \
            --with tox-uv \
            tox -e doc
        mkdir -p $READTHEDOCS_OUTPUT
        mv docs/_build/html $READTHEDOCS_OUTPUT
    """).strip()
    __update_build_step(
        config,
        new_command,
        search_function=lambda command: "pixi" in command,
    )


def _update_build_step_for_uv(config: ReadTheDocs) -> None:
    new_command = "export UV_LINK_MODE=copy"
    if "uv.lock" in set(git_ls_files(untracked=True)):
        new_command += dedent(R"""
            uv run \
              --group doc \
              --no-dev \
              --with tox-uv \
              tox -e doc
        """)
    else:
        new_command += dedent(R"""
            uv run \
              --group doc \
              --no-dev \
              --with tox-uv \
              tox -e doc
        """)
    new_command += dedent(R"""
        mkdir -p $READTHEDOCS_OUTPUT
        mv docs/_build/html $READTHEDOCS_OUTPUT
    """).strip()
    __update_build_step(
        config,
        new_command,
        search_function=lambda command: (
            "python3 -m sphinx" in command
            or "sphinx-build" in command
            or "tox -e" in command
        ),
    )


def __update_build_step(
    config: ReadTheDocs, new_command: str, search_function: Callable[[str], bool]
) -> None:
    commands = __get_commands(config)
    idx = None
    for i, command in enumerate(commands):
        if search_function(command):
            idx = i
            break
    if idx is None:
        commands.append(LiteralScalarString(new_command))
    elif commands[idx] != new_command:
        commands[idx] = LiteralScalarString(new_command)
    else:
        return
    msg = "Updated Sphinx build step in Read the Docs"
    config.changelog.append(msg)


def _update_post_install(
    config: ReadTheDocs,
    python_version: PythonVersion,
    package_manager: PackageManagerChoice,
) -> None:
    jobs = get_nested_dict(config.document, ["build", "jobs"])
    steps: list[str] = jobs.get("post_install", [])
    expected_pip_install_steps = __get_install_steps(python_version, package_manager)
    start = __find_step(steps, pattern=".*pip install.*")
    if start is None:
        start = 0
    end = __find_step(steps, pattern=".*(pip install|uv sync).*", invert=True)
    if end is None:
        end = len(steps)
    existing_pip_install_steps = steps[start:end]
    if existing_pip_install_steps == expected_pip_install_steps:
        return
    jobs["post_install"] = [
        *steps[:start],
        *expected_pip_install_steps,
        *steps[end:],
    ]
    msg = "Updated pip install steps"
    config.changelog.append(msg)


def __get_install_steps(
    python_version: PythonVersion,
    package_manager: PackageManagerChoice,
) -> list[str]:
    pip_install = "python -m uv pip install"
    constraints_file = get_constraints_file(python_version)
    if package_manager == "uv":
        install_statement = "python -m uv sync --group=doc --no-dev"
    elif constraints_file is None:
        install_statement = f"{pip_install} -e .[doc]"
    else:
        install_statement = f"{pip_install} -c {constraints_file} -e .[doc]"
    return [
        "python -m pip install 'uv>=0.2.0'",
        install_statement,
    ]


def __find_step(steps: list[str], pattern: str, invert: bool = False) -> int | None:
    for idx, step in enumerate(steps):
        if invert:
            if re.match(pattern, step) is None:
                return idx
        elif re.match(pattern, step) is not None:
            return idx
    return None


class ReadTheDocs:
    def __init__(self, source: IO | Path | str) -> None:
        self.__parser = create_prettier_round_trip_yaml()
        self.changelog: list[str] = []
        self.source = source
        if isinstance(source, (Path, str)):
            with open(source) as f:
                self.document = cast("dict", self.__parser.load(f))
        else:
            self.document = cast("dict", self.__parser.load(source))

    def dump(self, target: IO | Path | str | None = None) -> None:
        if target is None:
            target = self.source
        if isinstance(target, (Path, str)):
            with open(target, "w") as f:
                self.__parser.dump(self.document, f)
        else:
            target.seek(0)
            self.__parser.dump(self.document, target)

    def finalize(self) -> None:
        if not self.changelog:
            return
        msg = f"Updated {CONFIG_PATH.readthedocs}:\n"
        msg += indent("\n".join(self.changelog), prefix="  - ")
        self.dump(self.source)
        raise PrecommitError(msg)
