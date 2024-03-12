"""Helper functions for modifying :file:`.pre-commit.config.yaml`."""

from __future__ import annotations

import io
from contextlib import AbstractContextManager
from pathlib import Path
from textwrap import indent
from typing import IO, TYPE_CHECKING, TypeVar

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit.getters import find_repo, find_repo_with_index
from compwa_policy.utilities.precommit.setters import (
    remove_precommit_hook,
    update_precommit_hook,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if TYPE_CHECKING:
    from types import TracebackType

    from ruamel.yaml import YAML

    from compwa_policy.utilities.precommit.struct import Hook, PrecommitConfig, Repo

T = TypeVar("T", bound="Precommit")


class Precommit:
    """Read-only representation of a :code:`.pre-commit-config.yaml` file."""

    def __init__(
        self, document: PrecommitConfig, parser: YAML, source: IO | Path | None = None
    ) -> None:
        self.__document = document
        self.__parser = parser
        self.__source = source

    @property
    def document(self) -> PrecommitConfig:
        return self.__document

    @property
    def parser(self) -> YAML:
        return self.__parser

    @property
    def source(self) -> IO | Path | None:
        return self.__source

    @classmethod
    def load(cls: type[T], source: IO | Path | str = CONFIG_PATH.precommit) -> T:
        """Load a :code:`pyproject.toml` file from a file, I/O stream, or `str`."""
        config, parser = _load_roundtrip_precommit_config(source)
        if isinstance(source, str):
            return cls(config, parser)
        return cls(config, parser, source)

    def dumps(self) -> str:
        with io.StringIO() as stream:
            self.parser.dump(self.document, stream)
            return stream.getvalue()

    def find_repo(self, search_pattern: str) -> Repo | None:
        """Find pre-commit repo definition in pre-commit config."""
        return find_repo(self.__document, search_pattern)

    def find_repo_with_index(self, search_pattern: str) -> tuple[int, Repo] | None:
        """Find pre-commit repo definition and its index in pre-commit config."""
        return find_repo_with_index(self.__document, search_pattern)


class ModifiablePrecommit(Precommit, AbstractContextManager):
    def __init__(
        self, document: PrecommitConfig, parser: YAML, source: IO | Path | None = None
    ) -> None:
        super().__init__(document, parser, source)
        self.__is_in_context = False
        self.__changelog: list[str] = []

    def __enter__(self) -> ModifiablePrecommit:
        self.__is_in_context = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if not self.__changelog:
            return
        if self.parser is None:
            self.dump(self.source)
        msg = "The following modifications were made"
        if isinstance(self.source, Path):
            msg += f" to {self.source}"
        msg += ":\n"
        msg += indent("\n".join(self.__changelog), prefix="  - ")
        raise PrecommitError(msg)

    def dump(self, target: IO | Path | str | None = None) -> None:
        if target is None:
            if self.source is None:
                msg = "Target required when source is not a file or I/O stream"
                raise ValueError(msg)
            target = self.source
        if isinstance(target, io.IOBase):
            current_position = target.tell()
            target.seek(0)
            self.parser.dump(self.document, target)
            target.seek(current_position)
        elif isinstance(target, Path):
            with open(target, "w") as stream:
                self.parser.dump(self.document, stream)
        else:
            msg = f"Target of type {type(target).__name__} is not supported"
            raise TypeError(msg)

    def append_to_changelog(self, message: str) -> None:
        self.__assert_is_in_context()
        self.__changelog.append(message)

    def __assert_is_in_context(self) -> None:
        if not self.__is_in_context:
            msg = "Modifications can only be made within a context"
            raise RuntimeError(msg)

    def remove_hook(self, hook_id: str, repo_url: str | None = None) -> None:
        self.__assert_is_in_context()
        remove_precommit_hook(self, hook_id, repo_url)

    def update_single_hook_repo(self, expected: Repo) -> None:
        self.__assert_is_in_context()
        update_single_hook_precommit_repo(self, expected)

    def update_hook(self, repo_url: str, expected_hook: Hook) -> None:
        self.__assert_is_in_context()
        update_precommit_hook(self, repo_url, expected_hook)


def _load_roundtrip_precommit_config(
    source: IO | Path | str = CONFIG_PATH.precommit,
) -> tuple[PrecommitConfig, YAML]:
    """Load the pre-commit config as a round-trip YAML object."""
    parser = create_prettier_round_trip_yaml()
    if isinstance(source, str):
        with io.StringIO(source) as stream:
            config = parser.load(stream)
    else:
        config = parser.load(source)
    return config, parser
