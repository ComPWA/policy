"""Helper functions for reading and writing to YAML files."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml
from ruamel.yaml import YAML

if TYPE_CHECKING:
    from pathlib import Path


class _IncreasedYamlIndent(yaml.Dumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:  # noqa: ARG002
        return super().increase_indent(flow, indentless=False)

    def write_line_break(self, data: str | None = None) -> None:
        """See https://stackoverflow.com/a/44284819."""
        super().write_line_break(data)
        if len(self.indents) == 1:
            super().write_line_break()


def create_prettier_round_trip_yaml() -> YAML:
    yaml_parser = YAML(typ="rt")
    yaml_parser.preserve_quotes = True
    yaml_parser.map_indent = 2
    yaml_parser.indent = 4
    yaml_parser.block_seq_indent = 2
    return yaml_parser


def read_preserved_yaml(src: str) -> Any:
    """Get a :code:`ruamel.yaml` object from a YAML string.

    >>> formatted_obj = read_preserved_yaml("[--line-length=85]")
    >>> formatted_obj
    ['--line-length=85']
    >>> type(formatted_obj)
    <class 'ruamel.yaml.comments.CommentedSeq'>
    """
    return YAML(typ="rt").load(src)


def write_yaml(definition: dict, output_path: Path | str) -> None:
    """Write a `dict` to disk with standardized YAML formatting."""
    with open(output_path, "w") as stream:
        yaml.dump(
            definition,
            stream,
            sort_keys=False,
            Dumper=_IncreasedYamlIndent,
            default_flow_style=False,
        )
