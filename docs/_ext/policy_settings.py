"""Render the generated policy settings schema in Sphinx."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.parsers.rst import directives
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from sphinx.directives.code import container_wrapper
from sphinx.util.docutils import SphinxDirective
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from sphinx.application import Sphinx

ROOT_TABLE = "tool.compwa.policy"


@dataclass(frozen=True)
class Setting:
    """One key-value pair in the generated TOML example."""

    table: str
    name: str
    value: Any
    description: str

    @property
    def path(self) -> str:
        return f"{self.table}.{self.name}"

    @property
    def anchor(self) -> str:
        return nodes.make_id(self.path)


class PolicySettingsDirective(SphinxDirective):
    """Render a copyable TOML example from the policy settings schema.

    Each key in the example is an anchor that sphinx-tippy turns into a tooltip with the
    description of that setting, see :func:`_register_tooltips`.
    """

    has_content = False
    option_spec = MappingProxyType({"caption": directives.unchanged_required})

    @override
    def run(self) -> list[nodes.Node]:
        settings = list(_iter_settings(_load_schema(self.env.srcdir.parent)))
        example: nodes.Node = nodes.raw("", _render_html(settings), format="html")
        self.set_source_info(example)
        caption = self.options.get("caption")
        if caption is not None:
            example = container_wrapper(self, example, caption)
        return [example]


def _load_schema(repo_dir: Path) -> dict[str, Any]:
    return json.loads((repo_dir / "compwa-policy.schema.json").read_text())


def _iter_settings(schema: dict[str, Any]) -> Iterator[Setting]:
    for table, properties in _iter_tables(ROOT_TABLE, schema["properties"]):
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
            yield Setting(table, name, value, field_schema.get("description", ""))


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


def _render_toml(settings: list[Setting]) -> tuple[str, dict[int, Setting]]:
    """Render the TOML example and map each of its lines to a setting.

    >>> settings = [Setting("tool.compwa.policy", "no-ruff", False, "")]
    >>> source, line_map = _render_toml(settings)
    >>> print(source)
    [tool.compwa.policy]
    no-ruff = false
    >>> line_map[1].name
    'no-ruff'
    """
    lines: list[str] = []
    line_map: dict[int, Setting] = {}
    table = None
    for setting in settings:
        if setting.table != table:
            if lines:
                lines.append("")
            lines.append(f"[{setting.table}]")
            table = setting.table
        line_map[len(lines)] = setting
        value = json.dumps(setting.value, ensure_ascii=False)
        lines.append(f"{setting.name} = {value}")
    return "\n".join(lines), line_map


_KEY_PATTERN = re.compile(r'^(<span class="[^"]+">)?(?P<key>[\w.-]+)(</span>)?')


def _render_html(settings: list[Setting]) -> str:
    source, line_map = _render_toml(settings)
    lexer = get_lexer_by_name("toml")
    highlighted = highlight(source, lexer, HtmlFormatter(nowrap=True))
    lines = highlighted.rstrip("\n").split("\n")
    for number, setting in line_map.items():
        lines[number] = _link_key(lines[number], setting)
    body = "\n".join(lines)
    return (
        '<div class="highlight-toml notranslate">'
        f'<div class="highlight"><pre>{body}</pre></div>'
        "</div>"
    )


def _link_key(line: str, setting: Setting) -> str:
    """Turn the highlighted key at the start of a line into a self-referencing anchor.

    The anchor is what sphinx-tippy attaches the tooltip to; it points to itself so that
    the key doubles as a permalink to the setting.

    >>> setting = Setting("tool.compwa.policy", "no-ruff", False, "")
    >>> _link_key('<span class="n">no-ruff</span> = false', setting)
    '<a class="policy-setting" id="tool-compwa-policy-no-ruff" href="#tool-compwa-policy-no-ruff"><span class="n">no-ruff</span></a> = false'
    """
    match = _KEY_PATTERN.match(line)
    if match is None or match.group("key") != setting.name:
        msg = f"Could not find key {setting.name} in highlighted line: {line}"
        raise ValueError(msg)
    anchor = setting.anchor
    link = (
        f'<a class="policy-setting" id="{anchor}" href="#{anchor}">{match.group()}</a>'
    )
    return link + line[match.end() :]


_LITERAL_PATTERN = re.compile(r"``(?P<text>[^`]+)``")


def _to_tooltip(description: str) -> str:
    """Convert a schema description to the HTML shown in its tooltip.

    Only inline literals are supported, as that is the only reStructuredText markup that
    the descriptions in the settings model use.

    >>> _to_tooltip("Run pytest without the parallel ``-n`` argument.")
    '<p>Run pytest without the parallel <code>-n</code> argument.</p>'
    """
    escaped = html.escape(description)
    body = _LITERAL_PATTERN.sub(r"<code>\g<text></code>", escaped)
    return f"<p>{body}</p>"


def _register_tooltips(app: Sphinx) -> None:
    """Feed the setting descriptions to sphinx-tippy as custom tips.

    Custom tips are keyed by the ``href`` of the anchors created by :func:`_link_key`,
    so the descriptions do not have to appear anywhere on the page itself.
    """
    settings = _iter_settings(_load_schema(app.srcdir.parent))
    app.config.tippy_custom_tips |= {
        f"#{setting.anchor}": _to_tooltip(setting.description) for setting in settings
    }


def setup(app: Sphinx) -> dict[str, bool]:
    app.add_directive("policy-settings", PolicySettingsDirective)
    app.add_css_file("policy-settings.css")
    app.connect("builder-inited", _register_tooltips, priority=400)
    return {"parallel_read_safe": True}
