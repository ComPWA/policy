"""Tools for loading, inspecting, and updating :code:`pyproject.toml`."""

from __future__ import annotations

import io
import sys
from collections import abc
from contextlib import AbstractContextManager
from pathlib import Path
from textwrap import indent
from typing import IO, TYPE_CHECKING, Any, Literal, TypeVar, final, overload

import rtoml
import tomlkit
from attrs import field, frozen

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
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
    split_dependency_definition,
)

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, MutableMapping, Sequence
    from types import TracebackType

    from compwa_policy.utilities.pyproject._struct import PyprojectTOML

T = TypeVar("T", bound="Pyproject")


@frozen
class Pyproject:
    """Read-only representation of a :code:`pyproject.toml` file."""

    _document: PyprojectTOML
    _source: IO | Path | None = field(default=None)

    @classmethod
    def load(cls: type[T], source: IO | Path | str = CONFIG_PATH.pyproject) -> T:
        """Load a :code:`pyproject.toml` file from a file, I/O stream, or `str`."""
        document = load_pyproject_toml(source, modifiable=False)
        if isinstance(source, str):
            return cls(document)
        return cls(document, source)

    def dumps(self) -> str:
        src = rtoml.dumps(self._document, pretty=True)
        return f"{src.strip()}\n"

    def get_table(self, dotted_header: str, create: bool = False) -> Mapping[str, Any]:
        if create:
            msg = "Cannot create sub-tables in a read-only pyproject.toml"
            raise TypeError(msg)
        return get_sub_table(self._document, dotted_header)

    @final
    def has_table(self, dotted_header: str) -> bool:
        return has_sub_table(self._document, dotted_header)

    @overload
    def get_package_name(self) -> str | None: ...
    @overload
    def get_package_name(self, *, raise_on_missing: Literal[False]) -> str | None: ...
    @overload
    def get_package_name(self, *, raise_on_missing: Literal[True]) -> str: ...
    @final
    def get_package_name(self, *, raise_on_missing: bool = False):  # type:ignore[no-untyped-def]
        return get_package_name(self._document, raise_on_missing)  # type:ignore[call-overload,reportCallIssue]

    @final
    def get_repo_url(self) -> str:
        """Extract the source URL from the project table in pyproject.toml.

        >>> Pyproject.load().get_repo_url()
        'https://github.com/ComPWA/policy'
        """
        return get_source_url(self._document)

    @final
    def get_supported_python_versions(self) -> list[PythonVersion]:
        """Extract sorted, supported Python versions from package classifiers.

        >>> Pyproject.load().get_supported_python_versions()
        ['3.9', '3.10', '3.11', '3.12']
        """
        return get_supported_python_versions(self._document)


@frozen
class ModifiablePyproject(Pyproject, AbstractContextManager):
    """Stateful representation of a :code:`pyproject.toml` file.

    Use this class to apply multiple modifications to a :code:`pyproject.toml` file in
    separate sub-hooks. The modifications are dumped once the context is exited.
    """

    _is_in_context = False
    _changelog: list[str] = field(factory=list)

    @override
    @classmethod
    def load(cls: type[T], source: IO | Path | str = CONFIG_PATH.pyproject) -> T:
        """Load a :code:`pyproject.toml` file from a file, I/O stream, or `str`."""
        if isinstance(source, io.IOBase):
            current_position = source.tell()
            source.seek(0)
            document = tomlkit.load(source)  # type:ignore[arg-type]
            source.seek(current_position)
            return cls(document, source)  # type:ignore[arg-type]
        if isinstance(source, Path):
            with open(source) as stream:
                document = tomlkit.load(stream)
            return cls(document, source)  # type:ignore[arg-type]
        if isinstance(source, str):
            document = tomlkit.loads(source)
            return cls(document)  # type:ignore[arg-type]
        msg = f"Source of type {type(source).__name__} is not supported"
        raise TypeError(msg)

    @override
    def dumps(self) -> str:
        src = tomlkit.dumps(self._document, sort_keys=True)
        return f"{src.strip()}\n"

    def __enter__(self) -> Self:
        object.__setattr__(self, "_is_in_context", True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is not None and not issubclass(exc_type, PrecommitError):
            return False
        if not self._changelog:
            return True
        if self._source is not None:
            self.dump(self._source)
        msg = "The following modifications were made"
        if isinstance(self._source, (Path, str)):
            msg += f" to {self._source}"
        msg += ":\n"
        msg += indent("\n".join(self._changelog), prefix="  - ")
        raise PrecommitError(msg)

    def dump(self, target: IO | Path | str | None = None) -> None:
        if target is None and self._source is None:
            msg = "Target required when source is not a file or I/O stream"
            raise ValueError(msg)
        if isinstance(target, io.IOBase):
            current_position = target.tell()
            target.seek(0)
            tomlkit.dump(self._document, target, sort_keys=True)
            target.seek(current_position)
        elif isinstance(target, (Path, str)):
            src = self.dumps()
            with open(target, "w") as stream:
                stream.write(src)
        else:
            msg = f"Target of type {type(target).__name__} is not supported"
            raise TypeError(msg)

    @override
    def get_table(
        self, dotted_header: str, create: bool = False
    ) -> MutableMapping[str, Any]:
        self.__assert_is_in_context()
        if create:
            create_sub_table(self._document, dotted_header)
        return super().get_table(dotted_header)  # type:ignore[return-value]

    def add_dependency(
        self,
        package: str,
        dependency_group: str | Sequence[str] | None = None,
        optional_key: str | Sequence[str] | None = None,
    ) -> None:
        self.__assert_is_in_context()
        updated = add_dependency(
            self._document, package, dependency_group, optional_key
        )
        if updated:
            msg = f"Listed {package} as a dependency"
            self._changelog.append(msg)

    def remove_dependency(
        self, package: str, ignored_sections: Iterable[str] | None = None
    ) -> None:
        self.__assert_is_in_context()
        updated = remove_dependency(self._document, package, ignored_sections)
        if updated:
            msg = f"Removed {package} from dependencies"
            self._changelog.append(msg)

    def __assert_is_in_context(self) -> None:
        if not self._is_in_context:
            msg = "Modifications can only be made within a context"
            raise RuntimeError(msg)

    @property
    def changelog(self) -> list[str]:
        self.__assert_is_in_context()
        return self._changelog


def complies_with_subset(
    settings: Mapping,
    minimal_settings: Mapping,
    *,
    exact_value_match: bool = True,
) -> bool:
    """Compare if a nested mapping fits inside another nested mapping.

    >>> complies_with_subset(
    ...     {"channels": ["conda-forge"]},
    ...     {"channels": ["conda-forge"], "platforms": ["linux-64"]},
    ... )
    False
    >>> complies_with_subset(
    ...     {"channels": ["conda-forge"], "platforms": ["linux-64"]},
    ...     {"channels": ["conda-forge"]},
    ... )
    True
    >>> complies_with_subset(
    ...     {"channels": ["conda-forge", "default"]},
    ...     {"channels": ["conda-forge"]},
    ...     exact_value_match=False,
    ... )
    True
    """
    if exact_value_match:
        return all(
            settings.get(key) == expected for key, expected in minimal_settings.items()
        )
    for key, expected in minimal_settings.items():
        if not _complies_minimally(settings.get(key), expected):
            return False
    return True


def _complies_minimally(obj: Any, other: Any) -> bool:
    if isinstance(other, abc.Mapping):
        return complies_with_subset(obj, other, exact_value_match=False)
    if isinstance(other, str):
        return obj == other
    if isinstance(obj, abc.Iterable):
        return set(other) <= set(obj)
    return obj == other


def has_pyproject_package_name() -> bool:
    if not CONFIG_PATH.pyproject.exists():
        return False
    pyproject = Pyproject.load()
    return pyproject.get_package_name() is not None


def has_dependency(pyproject: Pyproject, package: str | tuple[str, ...]) -> bool:
    toml_document: PyprojectTOML = pyproject._document  # noqa: SLF001
    dependencies = set(toml_document.get("project", {}).get("dependencies", []))
    for group in toml_document.get("dependency-groups", {}).values():
        dependencies |= {x for x in group if isinstance(x, str)}
    if isinstance(package, str):
        packages_to_search = {package}
    else:
        packages_to_search = set(package)
    for dependency in dependencies:
        dependency_name, *_ = split_dependency_definition(dependency)
        if dependency_name.lower() in packages_to_search:
            return True
    return False


def get_constraints_file(python_version: PythonVersion) -> Path | None:
    path = CONFIG_PATH.pip_constraints / f"py{python_version}.txt"
    if path.exists():
        return path
    return None


def load_pyproject_toml(source: IO | Path | str, modifiable: bool) -> PyprojectTOML:
    """Load a :code:`pyproject.toml` file from a file, I/O stream, or `str`.

    The :code:`modifiable` flag determines which parser to use:

    - `False`: use `rtoml <https://github.com/samuelcolvin/rtoml>`_, which is
      **faster**, but does not preserve comments and formatting.
    - `True`: uses :mod:`tomlkit`, which is **slower**, but preservers comments and
      formatting.
    """
    parser = tomlkit if modifiable else rtoml
    if isinstance(source, io.IOBase):
        current_position = source.tell()
        source.seek(0)
        document = parser.load(source)
        source.seek(current_position)
        return document
    if isinstance(source, Path):
        with open(source) as stream:
            return parser.load(stream)  # type:ignore[return-value]
    if isinstance(source, str):
        return parser.loads(source)  # type:ignore[return-value]
    msg = f"Source of type {type(source).__name__} is not supported"
    raise TypeError(msg)
