"""Collection of helper functions that are shared by all sub-hooks."""

import io
import os
import re
from pathlib import Path
from typing import List, NamedTuple, Union

import repoma
from repoma.errors import PrecommitError


class _ConfigFilePaths(NamedTuple):
    cspell: Path = Path(".cspell.json")
    editor_config: Path = Path(".editorconfig")
    flake8: Path = Path(".flake8")
    github_workflow_dir: Path = Path(".github/workflows")
    gitpod: Path = Path(".gitpod.yml")
    pip_constraints: Path = Path(".constraints")
    precommit: Path = Path(".pre-commit-config.yaml")
    prettier: Path = Path(".prettierrc")
    prettier_ignore: Path = Path(".prettierignore")
    pydocstyle: Path = Path(".pydocstyle")
    pyproject: Path = Path("pyproject.toml")
    pytest: Path = Path("pytest.ini")
    setup_cfg: Path = Path("setup.cfg")
    tox: Path = Path("tox.ini")
    readme: Path = Path("README.md")
    vscode_extensions: Path = Path(".vscode/extensions.json")


CONFIG_PATH = _ConfigFilePaths()

REPOMA_DIR = Path(repoma.__file__).parent.absolute()


def read(input: Union[Path, io.TextIOBase, str]) -> str:  # noqa: A002
    if isinstance(input, (Path, str)):
        with open(input) as input_stream:
            return input_stream.read()
    if isinstance(input, io.TextIOBase):
        return input.read()
    raise TypeError(f"Cannot read from {type(input).__name__}")


def write(content: str, target: Union[Path, io.TextIOBase, str]) -> None:
    if isinstance(target, str):
        target = Path(target)
    if isinstance(target, Path):
        target.parent.mkdir(exist_ok=True)
        with open(target, "w") as output_stream:
            output_stream.write(content)
    elif isinstance(target, io.TextIOBase):
        target.write(content)
    else:
        raise TypeError(f"Cannot write from {type(target).__name__}")


def rename_file(old: str, new: str) -> None:
    """Rename a file and raise a `.PrecommitError`."""
    if os.path.exists(old):
        os.rename(old, new)
        raise PrecommitError(f"File {old} has been renamed to {new}")


def natural_sorting(text: str) -> List[Union[float, str]]:
    # https://stackoverflow.com/a/5967539/13219025
    return [
        __attempt_number_cast(c)
        for c in re.split(r"[+-]?([0-9]+(?:[.][0-9]*)?|[.][0-9]+)", text)
    ]


def __attempt_number_cast(text: str) -> Union[float, str]:
    try:
        return float(text)
    except ValueError:
        return text
