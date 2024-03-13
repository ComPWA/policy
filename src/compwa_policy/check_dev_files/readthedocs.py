"""Update Read the Docs configuration."""

from __future__ import annotations

from pathlib import Path
from textwrap import indent
from typing import IO, TYPE_CHECKING, cast

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import get_constraints_file
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from compwa_policy.utilities.pyproject.getters import PythonVersion


def main(
    python_version: PythonVersion, source: IO | Path | str = CONFIG_PATH.readthedocs
) -> None:
    if isinstance(source, str):
        source = Path(source)
    if isinstance(source, Path) and not source.exists():
        return
    rtd = ReadTheDocs(source)
    _update_os(rtd)
    _update_python_version(rtd, python_version)
    _update_install_step(rtd, python_version)
    rtd.finalize()


def _update_os(config: ReadTheDocs) -> None:
    build = cast(CommentedMap, config.document.get("build"))
    if build is None:
        return
    os: str | None = build.get("os")
    expected_os = "ubuntu-22.04"
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


def _update_install_step(config: ReadTheDocs, python_version: PythonVersion) -> None:
    steps = cast(
        list[str],
        config.document.get("build", {}).get("jobs", {}).get("post_install"),
    )
    if steps is None:
        return
    if len(steps) == 0:
        return
    step_idx = __find_pip_install_step(steps)
    if step_idx is None:
        return
    expected_steps = __get_install_steps(python_version)
    start = min(0, step_idx - len(expected_steps) - 1)
    end = step_idx + 1
    existing_steps = tuple(steps[start:end])
    if existing_steps == expected_steps:
        return
    steps.clear()  # update the reference in the post_install dict!
    steps.extend([
        *steps[:start],
        *expected_steps,
        *steps[end:],
    ])
    msg = "Updated pip install steps"
    config.changelog.append(msg)


def __get_install_steps(python_version: PythonVersion) -> tuple[str, str, str]:
    pip_install = "uv pip install --system"
    constraints_file = get_constraints_file(python_version)
    if constraints_file is None:
        install_statement = f"{pip_install} -e .[doc]"
    else:
        install_statement = f"{pip_install} -c {constraints_file} -e .[doc]"
    return (
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "source $HOME/.cargo/env",
        install_statement,
    )


def __find_pip_install_step(post_install: list[str]) -> int | None:
    for idx, step in enumerate(post_install):
        if "pip install" in step:
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
