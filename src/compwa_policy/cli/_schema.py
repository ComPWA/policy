"""Generate the JSON Schema for the public policy TOML configuration."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from compwa_policy.cli._settings import Settings, policy_sub_table

SCHEMA_PATH = Path("compwa-policy.schema.json")


def create_policy_schema() -> dict[str, Any]:
    """Project the runtime settings schema onto ``[tool.compwa.policy]``."""
    settings_schema = Settings.model_json_schema()
    properties = settings_schema.pop("properties")
    root_properties: dict[str, Any] = {}
    sub_tables: dict[str, dict[str, Any]] = {}
    for field_name, field_schema in properties.items():
        if field_name == "python":
            continue
        key = field_name.replace("_", "-")
        if field_name == "environment_variables":
            setup = sub_tables.setdefault("setup", {})
            setup["env"] = {
                "type": "object",
                "additionalProperties": {"type": "string"},
            }
            continue
        table = policy_sub_table(field_name)
        if table is None:
            root_properties[key] = deepcopy(field_schema)
        else:
            sub_tables.setdefault(table, {})[key] = deepcopy(field_schema)
    for table, table_properties in sub_tables.items():
        root_properties[table] = {
            "type": "object",
            "x-tombi-table-keys-order": "ascending",
            "properties": dict(sorted(table_properties.items())),
            "additionalProperties": False,
        }
    return {
        "$schema": settings_schema.get(
            "$schema", "https://json-schema.org/draft/2020-12/schema"
        ),
        "title": "ComPWA policy configuration",
        "description": "Configuration for the tool.compwa.policy TOML table.",
        "type": "object",
        "x-tombi-table-keys-order": "ascending",
        "properties": dict(sorted(root_properties.items())),
        "additionalProperties": False,
        **({"$defs": settings_schema["$defs"]} if "$defs" in settings_schema else {}),
    }


def render_policy_schema() -> str:
    """Render the generated schema in its committed representation."""
    return json.dumps(create_policy_schema(), indent=2) + "\n"
