"""Tools for loading, inspecting, and updating :code:`pyproject.toml`."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from textwrap import indent
from typing import IO, TYPE_CHECKING, Iterable, Sequence, overload

import tomlkit
from attrs import field, frozen

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.cfg import open_config
from compwa_policy.utilities.pyproject.getters import (
    PythonVersion,
    get_package_name,
    get_source_url,
    get_sub_table,
    get_supported_python_versions,
    has_sub_table,
)
from compwa_policy.utilities.pyproject.setters import (
    add_dependency,
    create_sub_table,
    remove_dependency,
)

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal
if TYPE_CHECKING:
    from tomlkit.items import Table
    from tomlkit.toml_document import TOMLDocument


@frozen
class PyprojectTOML:
    """Stateful representation of a :code:`pyproject.toml` file.

    Use this class to apply multiple modifications to a :code:`pyproject.toml` file in
    separate sub-hooks. The :meth:`.finalize` method should be called after all the
    modifications have been applied.
    """

    document: TOMLDocument
    source: IO | Path | None = field(default=None)
    modifications: list[str] = field(factory=list, init=False)

    @classmethod
    def load(cls, source: IO | Path | str = CONFIG_PATH.pyproject) -> PyprojectTOML:
        """Load a :code:`pyproject.toml` file from a file, I/O stream, or `str`."""
        if isinstance(source, io.IOBase):
            current_position = source.tell()
            source.seek(0)
            document = tomlkit.load(source)  # type:ignore[arg-type]
            source.seek(current_position)
            return cls(document, source)
        if isinstance(source, Path):
            with open(source) as stream:
                document = tomlkit.load(stream)
            return cls(document, source)
        if isinstance(source, str):
            return cls(tomlkit.loads(source))
        msg = f"Source of type {type(source).__name__} is not supported"
        raise TypeError(msg)

    def dump(self, target: IO | Path | str | None = None) -> None:
        if target is None and self.source is None:
            msg = "Target required when source is not a file or I/O stream"
            raise ValueError(msg)
        if isinstance(target, io.IOBase):
            current_position = target.tell()
            target.seek(0)
            tomlkit.dump(self.document, target, sort_keys=True)
            target.seek(current_position)
        elif isinstance(target, (Path, str)):
            src = self.dumps()
            with open(target, "w") as stream:
                stream.write(src)
        else:
            msg = f"Target of type {type(target).__name__} is not supported"
            raise TypeError(msg)

    def dumps(self) -> str:
        src = tomlkit.dumps(self.document, sort_keys=True)
        return f"{src.strip()}\n"

    def finalize(self) -> None:
        """If `modifications` were made, :meth:`dump` and raise `.PrecommitError`."""
        if not self.modifications:
            return
        self.dump(self.source)
        msg = "Following modifications were made"
        if isinstance(self.source, (Path, str)):
            msg = f" to {self.source}"
        msg += ":\n\n"
        modifications = indent("\n".join(self.modifications), prefix="   - ")
        self.modifications.clear()
        raise PrecommitError(modifications)

    def __del__(self) -> None:
        if self.modifications:
            msg = "Modifications were made, but finalize was not called"
            raise RuntimeError(msg)

    def get_table(self, dotted_header: str, create: bool = False) -> Table:
        if create:
            create_sub_table(self.document, dotted_header)
        return get_sub_table(self.document, dotted_header)

    def has_table(self, dotted_header: str) -> bool:
        return has_sub_table(self.document, dotted_header)

    @overload
    def get_package_name(self) -> str | None: ...
    @overload
    def get_package_name(self, *, raise_on_missing: Literal[False]) -> str | None: ...
    @overload
    def get_package_name(self, *, raise_on_missing: Literal[True]) -> str: ...
    def get_package_name(self, *, raise_on_missing: bool = False):  # type:ignore[no-untyped-def]
        return get_package_name(self.document, raise_on_missing)  # type:ignore[call-overload,reportCallIssue]

    def get_repo_url(self) -> str:
        """Extract the source URL from the project table in pyproject.toml.

        >>> PyprojectTOML.load().get_repo_url()
        'https://github.com/ComPWA/policy'
        """
        return get_source_url(self.document)

    def get_supported_python_versions(self) -> list[PythonVersion]:
        """Extract sorted, supported Python versions from package classifiers.

        >>> PyprojectTOML.load().get_supported_python_versions()
        ['3.7', '3.8', '3.9', '3.10', '3.11', '3.12']
        """
        return get_supported_python_versions(self.document)

    def add_dependency(
        self, package: str, optional_key: str | Sequence[str] | None = None
    ) -> None:
        updated = add_dependency(self.document, package, optional_key)
        if updated:
            msg = f"Listed {package} as a dependency"
            self.modifications.append(msg)

    def remove_dependency(
        self, package: str, ignored_sections: Iterable[str] | None = None
    ) -> None:
        updated = remove_dependency(self.document, package, ignored_sections)
        if updated:
            msg = f"Removed {package} from dependencies"
            self.modifications.append(msg)


def complies_with_subset(settings: dict, minimal_settings: dict) -> bool:
    return all(settings.get(key) == value for key, value in minimal_settings.items())


def get_build_system() -> Literal["pyproject", "setup.cfg"] | None:
    if _has_setup_cfg_build_system():
        return "setup.cfg"
    if not CONFIG_PATH.pyproject.exists():
        return None
    pyproject = PyprojectTOML.load()
    if pyproject.get_package_name() is None:
        return None
    return "pyproject"


def get_constraints_file(python_version: PythonVersion) -> Path | None:
    path = CONFIG_PATH.pip_constraints / f"py{python_version}.txt"
    if path.exists():
        return path
    return None


def _has_setup_cfg_build_system() -> bool:
    if not CONFIG_PATH.setup_cfg.exists():
        return False
    cfg = open_config(CONFIG_PATH.setup_cfg)
    return cfg.has_section("metadata")
