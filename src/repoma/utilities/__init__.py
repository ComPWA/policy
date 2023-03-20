"""Collection of helper functions that are shared by all sub-hooks."""

import io
import os
import re
from pathlib import Path
from shutil import copyfile
from typing import List, NamedTuple, Union

import repoma
from repoma.errors import PrecommitError


class _ConfigFilePaths(NamedTuple):
    codecov: Path = Path("codecov.yml")
    commitlint: Path = Path("commitlint.config.js")
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
    readme: Path = Path("README.md")
    readthedocs: Path = Path(".readthedocs.yml")
    release_drafter_config: Path = Path(".github/release-drafter.yml")
    release_drafter_workflow: Path = Path(".github/workflows/release-drafter.yml")
    setup_cfg: Path = Path("setup.cfg")
    taplo: Path = Path(".taplo.toml")
    tox: Path = Path("tox.ini")
    vscode_settings: Path = Path(".vscode/settings.json")
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


def update_file(relative_path: Path, in_template_folder: bool = False) -> None:
    if in_template_folder:
        template_dir = REPOMA_DIR / ".template"
    else:
        template_dir = REPOMA_DIR
    template_path = template_dir / relative_path
    if not os.path.exists(relative_path):
        copyfile(template_path, relative_path)
        raise PrecommitError(
            f"{relative_path} is missing, so created a new one. Please commit it."
        )
    with open(template_path) as f:
        expected_content = f.read()
    with open(relative_path) as f:
        existing_content = f.read()
    if expected_content != existing_content:
        copyfile(template_path, relative_path)
        raise PrecommitError(f"{relative_path} has been updated.")


def __attempt_number_cast(text: str) -> Union[float, str]:
    try:
        return float(text)
    except ValueError:
        return text
