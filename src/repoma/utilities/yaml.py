"""Helper functions for reading and writing to YAML files."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from ruamel.yaml import YAML

if TYPE_CHECKING:
    from pathlib import Path


class _IncreasedYamlIndent(yaml.Dumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, indentless=False)

    def write_line_break(self, data: str | None = None) -> None:
        """See https://stackoverflow.com/a/44284819."""
        super().write_line_break(data)
        if len(self.indents) == 1:
            super().write_line_break()


def create_prettier_round_trip_yaml() -> YAML:
    yaml_parser = YAML(typ="rt")
    yaml_parser.preserve_quotes = True  # type: ignore[assignment]
    yaml_parser.map_indent = 2  # type: ignore[assignment]
    yaml_parser.indent = 4
    yaml_parser.block_seq_indent = 2
    return yaml_parser


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
