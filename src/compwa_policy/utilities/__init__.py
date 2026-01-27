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

import compwa_policy
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.executor import Executor


class _ConfigFilePaths(NamedTuple):
    binder: Path = Path(".binder")
    citation: Path = Path("CITATION.cff")
    codecov: Path = Path("codecov.yml")
    conda: Path = Path("environment.yml")
    cspell: Path = Path(".cspell.json")
    editorconfig: Path = Path(".editorconfig")
    envrc: Path = Path(".envrc")
    gitattributes: Path = Path(".gitattributes")
    github_workflow_dir: Path = Path(".github/workflows")
    gitignore: Path = Path(".gitignore")
    gitpod: Path = Path(".gitpod.yml")
    pip_constraints: Path = Path(".constraints")
    pixi_lock: Path = Path("pixi.lock")
    pixi_toml: Path = Path("pixi.toml")
    precommit: Path = Path(".pre-commit-config.yaml")
    prettier_ignore: Path = Path(".prettierignore")
    pyproject: Path = Path("pyproject.toml")
    pytest_ini: Path = Path("pytest.ini")
    readme: Path = Path("README.md")
    readthedocs: Path = Path(".readthedocs.yml")
    release_drafter_config: Path = Path(".github/release-drafter.yml")
    release_drafter_workflow: Path = Path(".github/workflows/release-drafter.yml")
    taplo: Path = Path(".taplo.toml")
    vscode_extensions: Path = Path(".vscode/extensions.json")
    vscode_settings: Path = Path(".vscode/settings.json")
    zenodo: Path = Path(".zenodo.json")


CONFIG_PATH = _ConfigFilePaths()
COMPWA_POLICY_DIR = Path(compwa_policy.__file__).parent.absolute()


def append_safe(expected_line: str, path: Path) -> bool:
    """Add a line to a file if it is not already present."""
    if path.exists() and contains_line(path, expected_line):
        return False
    with path.open("a") as stream:
        stream.write(expected_line + "\n")
    return True


def contains_line(input: Path | io.TextIOBase | str, expected_line: str) -> bool:  # noqa: A002
    if isinstance(input, io.TextIOBase):
        lines = input.readlines()
    else:
        with open(input) as stream:
            lines = stream.readlines()
    return expected_line in {line.strip() for line in lines}


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


def read(input: Path | io.TextIOBase | str) -> str:  # noqa: A002
    if isinstance(input, (Path, str)):
        with open(input) as input_stream:
            return input_stream.read()
    if isinstance(input, io.TextIOBase):
        return input.read()
    msg = f"Cannot read from {type(input).__name__}"
    raise TypeError(msg)


def write(content: str, target: Path | io.TextIOBase | str) -> None:
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
    with Executor() as do:
        for path in paths:
            do(__remove_file, path)


def __remove_file(path: str) -> None:
    if not os.path.exists(path):
        return
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    msg = f"Removed {path}"
    raise PrecommitError(msg)


def rename_file(old: str, new: str) -> None:
    """Rename a file and raise a `.PrecommitError`."""
    if os.path.exists(old):
        os.rename(old, new)
        msg = f"File {old} has been renamed to {new}"
        raise PrecommitError(msg)


def remove_lines(file: Path, pattern: str, flags: re.RegexFlag = re.IGNORECASE) -> None:
    if not file.exists():
        return
    with open(file) as stream:
        lines = stream.readlines()
    filtered_lines = [s for s in lines if not re.match(pattern, s.strip(), flags)]
    if not any(line.strip() for line in filtered_lines):
        file.unlink()
        msg = f"Removed {pattern!r} from {file} and removed file because it was empty."
        raise PrecommitError(msg)
    if len(filtered_lines) == len(lines):
        return
    with open(file, "w") as stream:
        stream.writelines(filtered_lines)
    msg = f"Removed {pattern!r} from {file}"
    raise PrecommitError(msg)


def natural_sorting(text: str) -> list[float | str]:
    # https://stackoverflow.com/a/5967539/13219025
    return [
        __attempt_number_cast(c)
        for c in re.split(r"[+-]?([0-9]+(?:[.][0-9]*)?|[.][0-9]+)", text)
    ]


def update_file(relative_path: Path, in_template_folder: bool = False) -> None:
    if in_template_folder:
        template_dir = COMPWA_POLICY_DIR / ".template"
    else:
        template_dir = COMPWA_POLICY_DIR
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


def get_nested_dict(data: dict, keys: list[str]) -> dict:
    """Get a nested dictionary from a list of keys, create it if it doesn't exist.

    >>> data = {}
    >>> sub_dict = get_nested_dict(data, keys=["a", "b"])
    >>> sub_dict["c"] = 1
    >>> data
    {'a': {'b': {'c': 1}}}
    """
    nested_dict = data
    for key in keys:
        if key not in nested_dict:
            nested_dict[key] = {}
        nested_dict = nested_dict[key]
    return nested_dict
