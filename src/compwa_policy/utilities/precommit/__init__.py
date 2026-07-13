"""Helper functions for modifying :file:`.pre-commit.config.yaml`."""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import IO, TYPE_CHECKING, TypeVar

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import CommentMark
from ruamel.yaml.tokens import CommentToken

from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit.getters import find_repo, find_repo_with_index
from compwa_policy.utilities.precommit.setters import (
    remove_precommit_hook,
    update_precommit_hook,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.resource import Changelog, ModifiableResource
from compwa_policy.utilities.yaml import create_prettier_round_trip_yaml

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from types import TracebackType

    from ruamel.yaml import YAML

    from compwa_policy.utilities.precommit.struct import Hook, PrecommitConfig, Repo

T = TypeVar("T", bound="Precommit")
_POST_VALUE_COMMENT_INDEX = 2
_SEQUENCE_ITEM_COMMENT_INDEX = 0


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
    def load(cls, source: IO | Path | str = CONFIG_PATH.precommit) -> Self:
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


class ModifiablePrecommit(Precommit, ModifiableResource):
    def __init__(
        self, document: PrecommitConfig, parser: YAML, source: IO | Path | None = None
    ) -> None:
        super().__init__(document, parser, source)
        self.__is_in_context = False
        self.__changelog: Changelog = []

    def __enter__(self) -> Self:
        self.__is_in_context = True
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _tb: TracebackType | None,
    ) -> bool:
        if self.__changelog and self.source is not None:
            self.dump(self.source)
        return False

    def dump(self, target: IO | Path | str | None = None) -> None:
        if target is None:
            if self.source is None:
                msg = "Target required when source is not a file or I/O stream"
                raise ValueError(msg)
            target = self.source
        _normalize_repo_spacing(self.document)
        if isinstance(target, io.IOBase):
            current_position = target.tell()
            target.seek(0)
            self.parser.dump(self.document, target)
            target.truncate()
            target.seek(current_position)
        elif isinstance(target, Path):
            with open(target, "w") as stream:
                self.parser.dump(self.document, stream)
        else:
            msg = f"Target of type {type(target).__name__} is not supported"
            raise TypeError(msg)

    @property
    def changelog(self) -> Changelog:
        self.__assert_is_in_context()
        return self.__changelog

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


def _normalize_repo_spacing(config: PrecommitConfig) -> None:
    repos = config.get("repos")
    if not isinstance(repos, CommentedSeq):
        return
    _remove_blank_lines(repos)
    for repo in repos[:-1]:
        _append_repo_separator(repo)


def _append_repo_separator(node: object) -> None:
    if isinstance(node, CommentedSeq) and node:
        last_index = len(node) - 1
        last_value = node[last_index]
        if isinstance(last_value, (CommentedMap, CommentedSeq)) and last_value:
            _append_repo_separator(last_value)
            return
        item_comments = node.ca.items.setdefault(
            last_index,
            [None, None, None, None],
        )
        _add_blank_line(item_comments, _SEQUENCE_ITEM_COMMENT_INDEX)
        return
    if not isinstance(node, CommentedMap) or not node:
        return
    last_key = next(reversed(node))
    last_value = node[last_key]
    if isinstance(last_value, (CommentedMap, CommentedSeq)) and last_value:
        _append_repo_separator(last_value)
        return
    item_comments = node.ca.items.setdefault(last_key, [None, None, None, None])
    _add_blank_line(item_comments, _POST_VALUE_COMMENT_INDEX)


def _add_blank_line(item_comments: list, comment_index: int) -> None:
    comment = item_comments[comment_index]
    if not isinstance(comment, CommentToken):
        item_comments[comment_index] = CommentToken("\n\n", CommentMark(0))
    elif comment.value.startswith("\n"):
        comment.value = f"\n{comment.value}"
    else:
        comment.value = f"{comment.value}\n"


def _remove_blank_lines(node: object) -> None:
    if isinstance(node, CommentedMap):
        node.ca.comment = _normalize_comments(node.ca.comment)
        node.ca.end = _normalize_comments(node.ca.end) or []
        for item_comments in node.ca.items.values():
            for index, comment in enumerate(item_comments):
                item_comments[index] = _normalize_comments(
                    comment,
                    keep_line_break=index == _POST_VALUE_COMMENT_INDEX,
                )
        for value in node.values():
            _remove_blank_lines(value)
    elif isinstance(node, CommentedSeq):
        node.ca.comment = _normalize_comments(node.ca.comment)
        node.ca.end = _normalize_comments(node.ca.end) or []
        for item_comments in node.ca.items.values():
            for index, comment in enumerate(item_comments):
                item_comments[index] = _normalize_comments(
                    comment,
                    keep_line_break=index == _SEQUENCE_ITEM_COMMENT_INDEX,
                )
        for value in node:
            _remove_blank_lines(value)


def _normalize_comments(comments: object, *, keep_line_break: bool = False) -> object:
    if isinstance(comments, CommentToken):
        comments.value = re.sub(r"\n[ \t]*(?=\n)", "", comments.value)
        if comments.value.strip() or keep_line_break:
            comments.value = comments.value or "\n"
            return comments
        return None
    if isinstance(comments, list):
        normalized = [
            comment
            for item in comments
            if (comment := _normalize_comments(item, keep_line_break=keep_line_break))
            is not None
        ]
        return normalized or None
    return comments
