"""Render the generated policy settings schema in Sphinx."""

from __future__ import annotations

import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.directives.code import container_wrapper
from sphinx.util.docutils import SphinxDirective
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sphinx.application import Sphinx


class PolicySettingsDirective(SphinxDirective):
    """Render a copyable TOML example from the policy settings schema."""

    has_content = False
    option_spec = MappingProxyType({"caption": directives.unchanged_required})

    @override
    def run(self) -> list[nodes.Node]:
        schema_path = self.env.srcdir.parent / "compwa-policy.schema.json"
        schema = json.loads(schema_path.read_text())
        source = _render_toml(schema)
        example = nodes.literal_block(source, source)
        example["language"] = "toml"
        caption = self.options.get("caption")
        if caption is not None:
            example = container_wrapper(self, example, caption)
        return [example]


def _render_toml(schema: dict[str, Any]) -> str:
    lines: list[str] = []
    for table, properties in _iter_tables("tool.compwa.policy", schema["properties"]):
        if lines:
            lines.append("")
        lines.append(f"[{table}]")
        for name, field_schema in properties.items():
            if field_schema.get("type") == "object":
                continue
            value = field_schema.get("default")
            if value is None:
                examples = field_schema.get("examples", [])
                if not examples:
                    continue
                value = examples[0]
            if value is None:
                continue
            description = field_schema.get("description")
            if description:
                lines.append(f"# {description}")
            lines.append(f"{name} = {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines)


def _iter_tables(
    table: str, properties: dict[str, Any]
) -> Iterator[tuple[str, dict[str, Any]]]:
    yield table, properties
    for name, field_schema in properties.items():
        if field_schema.get("type") != "object":
            continue
        nested_properties = field_schema.get("properties")
        if nested_properties is not None:
            yield from _iter_tables(f"{table}.{name}", nested_properties)


def setup(app: Sphinx) -> dict[str, bool]:
    app.add_directive("policy-settings", PolicySettingsDirective)
    return {"parallel_read_safe": True}
