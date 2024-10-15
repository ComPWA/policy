"""Update Read the Docs configuration."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent, indent
from typing import IO, TYPE_CHECKING, cast

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, LiteralScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, get_nested_dict
from compwa_policy.utilities.pyproject import get_constraints_file
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
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
    _update_os(rtd)
    _update_python_version(rtd, python_version)
    if "uv" in package_manager or "pixi" in package_manager:
        if "uv" in package_manager:
            _install_asdf_plugin(rtd, "uv")
        if "pixi" in package_manager:
            _install_asdf_plugin(rtd, "pixi")
        _remove_redundant_settings(rtd)
    else:
        _update_post_install(rtd, python_version, package_manager)
    rtd.finalize()


def _update_os(config: ReadTheDocs) -> None:
    build = cast(CommentedMap, config.document.get("build"))
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
    tools = cast(CommentedMap, config.document.get("build", {}).get("tools"))
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


def _install_asdf_plugin(config: ReadTheDocs, plugin_name: str) -> None:
    if "build" not in config.document:
        config.document["build"] = {}
    commands: list[str] = config.document["build"]["commands"]
    cmd = dedent(f"""
        asdf plugin add {plugin_name}
        asdf install {plugin_name} latest
        asdf global {plugin_name} latest
    """).strip()
    if cmd in commands:
        return
    commands.insert(0, LiteralScalarString(cmd))
    msg = f"Added asdf plugin installation for {plugin_name}"
    config.changelog.append(msg)


def _remove_redundant_settings(config: ReadTheDocs) -> None:
    redundant_keys = [
        "build.apt_packages",
        "build.jobs",
        "formats",
        "sphinx",
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
        install_statement = "python -m uv sync --extra=doc"
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
                self.document = cast(dict, self.__parser.load(f))
        else:
            self.document = cast(dict, self.__parser.load(source))

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
