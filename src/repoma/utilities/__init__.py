"""Collection of helper functions that are shared by all sub-hooks."""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
from pathlib import Path
from shutil import copyfile
from typing import NamedTuple

import repoma
from repoma.errors import PrecommitError
from repoma.utilities.executor import Executor


class _ConfigFilePaths(NamedTuple):
    citation: Path = Path("CITATION.cff")
    codecov: Path = Path("codecov.yml")
    cspell: Path = Path(".cspell.json")
    editorconfig: Path = Path(".editorconfig")
    github_workflow_dir: Path = Path(".github/workflows")
    gitpod: Path = Path(".gitpod.yml")
    pip_constraints: Path = Path(".constraints")
    precommit: Path = Path(".pre-commit-config.yaml")
    prettier: Path = Path(".prettierrc")
    prettier_ignore: Path = Path(".prettierignore")
    pyproject: Path = Path("pyproject.toml")
    readme: Path = Path("README.md")
    readthedocs: Path = Path(".readthedocs.yml")
    release_drafter_config: Path = Path(".github/release-drafter.yml")
    release_drafter_workflow: Path = Path(".github/workflows/release-drafter.yml")
    setup_cfg: Path = Path("setup.cfg")
    taplo: Path = Path(".taplo.toml")
    tox: Path = Path("tox.ini")
    vscode_extensions: Path = Path(".vscode/extensions.json")
    vscode_settings: Path = Path(".vscode/settings.json")
    zenodo: Path = Path(".zenodo.json")


CONFIG_PATH = _ConfigFilePaths()
REPOMA_DIR = Path(repoma.__file__).parent.absolute()


def hash_file(path: Path | str) -> str:
    # https://stackoverflow.com/a/22058673
    buffer_size = 65_536
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(buffer_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def read(input: Path | (io.TextIOBase | str)) -> str:  # noqa: A002
    if isinstance(input, (Path, str)):
        with open(input) as input_stream:
            return input_stream.read()
    if isinstance(input, io.TextIOBase):
        return input.read()
    msg = f"Cannot read from {type(input).__name__}"
    raise TypeError(msg)


def write(content: str, target: Path | (io.TextIOBase | str)) -> None:
    if isinstance(target, str):
        target = Path(target)
    if isinstance(target, Path):
        target.parent.mkdir(exist_ok=True)
        with open(target, "w") as output_stream:
            output_stream.write(content)
    elif isinstance(target, io.TextIOBase):
        target.write(content)
    else:
        msg = f"Cannot write from {type(target).__name__}"
        raise TypeError(msg)


def remove_configs(paths: list[str]) -> None:
    executor = Executor()
    for path in paths:
        executor(__remove_file, path)
    executor.finalize()


def __remove_file(path: str) -> None:
    if not os.path.exists(path):
        return
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    msg = f"Removed {path}"
    raise PrecommitError(msg)


def remove_from_gitignore(pattern: str) -> None:
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        return
    with open(gitignore_path) as f:
        lines = f.readlines()
    filtered_lines = [s for s in lines if pattern not in s]
    if filtered_lines == lines:
        return
    with open(gitignore_path, "w") as f:
        f.writelines(filtered_lines)
    msg = f"Removed {pattern} from {gitignore_path}"
    raise PrecommitError(msg)


def rename_file(old: str, new: str) -> None:
    """Rename a file and raise a `.PrecommitError`."""
    if os.path.exists(old):
        os.rename(old, new)
        msg = f"File {old} has been renamed to {new}"
        raise PrecommitError(msg)


def natural_sorting(text: str) -> list[float | str]:
    # https://stackoverflow.com/a/5967539/13219025
    return [
        __attempt_number_cast(c)
        for c in re.split(r"[+-]?([0-9]+(?:[.][0-9]*)?|[.][0-9]+)", text)
    ]


def update_file(relative_path: Path, in_template_folder: bool = False) -> None:
    if in_template_folder:
        template_dir = REPOMA_DIR / ".template"
    else:
        template_dir = REPOMA_DIR
    template_path = template_dir / relative_path
    if not os.path.exists(relative_path):
        copyfile(template_path, relative_path)
        msg = f"{relative_path} is missing, so created a new one. Please commit it."
        raise PrecommitError(msg)
    with open(template_path) as f:
        expected_content = f.read()
    with open(relative_path) as f:
        existing_content = f.read()
    if expected_content != existing_content:
        copyfile(template_path, relative_path)
        msg = f"{relative_path} has been updated."
        raise PrecommitError(msg)


def __attempt_number_cast(text: str) -> float | str:
    try:
        return float(text)
    except ValueError:
        return text
