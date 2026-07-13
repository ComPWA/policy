"""Collection of helper functions that are shared by all sub-hooks."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import compwa_policy
from compwa_policy.utilities.resource import ModifiablePath

if TYPE_CHECKING:
    from compwa_policy.utilities.session import Changelog, Session


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


def append_safe(
    expected_line: str, path: Path, *, session: Session | None = None
) -> bool:
    """Add a line to a file if it is not already present."""
    resource = _get_path_resource(path, session=session)
    lines = resource.read_text().splitlines() if resource.exists else []
    if expected_line in {line.strip() for line in lines}:
        return False
    content = resource.read_text() if resource.exists else ""
    resource.write_text(content + expected_line + "\n")
    _dump_without_session(resource, session=session)
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


def read(
    input: Path | io.TextIOBase | str,  # noqa: A002
    *,
    session: Session | None = None,
) -> str:
    if isinstance(input, (Path, str)):
        if session is not None:
            return _get_path_resource(input, session=session).read_text()
        with open(input) as input_stream:
            return input_stream.read()
    if isinstance(input, io.TextIOBase):
        return input.read()
    msg = f"Cannot read from {type(input).__name__}"
    raise TypeError(msg)


def write(
    content: str,
    target: Path | io.TextIOBase | str,
    *,
    session: Session | None = None,
) -> None:
    if isinstance(target, str):
        target = Path(target)
    if isinstance(target, Path):
        if session is not None:
            _get_path_resource(target, session=session).write_text(content)
            return
        target.parent.mkdir(exist_ok=True)
        with open(target, "w") as output_stream:
            output_stream.write(content)
    elif isinstance(target, io.TextIOBase):
        target.write(content)
    else:
        msg = f"Cannot write from {type(target).__name__}"
        raise TypeError(msg)


def remove_configs(paths: list[str], *, session: Session | None = None) -> Changelog:
    changes: Changelog = []
    for path in paths:
        resource = _get_path_resource(path, session=session)
        message = f"Removed {path}"
        if resource.remove(message):
            changes.append(message)
            _dump_without_session(resource, session=session)
    return [] if session is not None else changes


def _get_path_resource(
    path: Path | str,
    *,
    session: Session | None = None,
) -> ModifiablePath:
    normalized = Path(path)
    if session is not None:
        return session.get_path(normalized)
    return ModifiablePath.load_path(normalized)


def _dump_without_session(
    resource: ModifiablePath,
    *,
    session: Session | None = None,
) -> None:
    if session is None and resource.changed:
        resource.dump()


def __remove_file(path: str, *, session: Session | None = None) -> Changelog:
    resource = _get_path_resource(path, session=session)
    message = f"Removed {path}"
    if not resource.remove(message):
        return []
    _dump_without_session(resource, session=session)
    if session is not None:
        return []
    return [message]


def rename_file(old: str, new: str, *, session: Session | None = None) -> Changelog:
    source = _get_path_resource(old, session=session)
    if not source.exists:
        return []
    content = source.read_text()
    message = f"File {old} has been renamed to {new}"
    target = _get_path_resource(new, session=session)
    target.write_text(content, message)
    source.remove()
    _dump_without_session(target, session=session)
    _dump_without_session(source, session=session)
    return [] if session is not None else [message]


def remove_lines(
    file: Path,
    pattern: str,
    flags: re.RegexFlag = re.IGNORECASE,
    *,
    session: Session | None = None,
) -> Changelog:
    resource = _get_path_resource(file, session=session)
    if not resource.exists:
        return []
    lines = resource.read_text().splitlines(True)
    filtered_lines = [s for s in lines if not re.match(pattern, s.strip(), flags)]
    if not any(line.strip() for line in filtered_lines):
        message = (
            f"Removed {pattern!r} from {file} and removed file because it was empty."
        )
        resource.remove(message)
        _dump_without_session(resource, session=session)
        return [] if session is not None else [message]
    if len(filtered_lines) == len(lines):
        return []
    message = f"Removed {pattern!r} from {file}"
    resource.write_text("".join(filtered_lines), message)
    _dump_without_session(resource, session=session)
    return [] if session is not None else [message]


def natural_sorting(text: str) -> list[float | str]:
    # https://stackoverflow.com/a/5967539/13219025
    return [
        __attempt_number_cast(c)
        for c in re.split(r"[+-]?([0-9]+(?:[.][0-9]*)?|[.][0-9]+)", text)
    ]


def update_file(
    relative_path: Path,
    in_template_folder: bool = False,
    *,
    session: Session | None = None,
) -> Changelog:
    if in_template_folder:
        template_dir = COMPWA_POLICY_DIR / ".template"
    else:
        template_dir = COMPWA_POLICY_DIR
    template_path = template_dir / relative_path
    expected_content = template_path.read_text()
    resource = _get_path_resource(relative_path, session=session)
    if not resource.exists:
        message = f"{relative_path} is missing, so created a new one. Please commit it."
        resource.write_text(expected_content, message)
        _dump_without_session(resource, session=session)
        return [] if session is not None else [message]
    existing_content = resource.read_text()
    if expected_content != existing_content:
        message = f"{relative_path} has been updated."
        resource.write_text(expected_content, message)
        _dump_without_session(resource, session=session)
        return [] if session is not None else [message]
    return []


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
