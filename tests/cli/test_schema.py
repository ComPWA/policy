from compwa_policy.cli._schema import create_policy_schema, render_policy_schema


def describe_create_policy_schema() -> None:
    def projects_settings_into_the_public_toml_shape() -> None:
        schema = create_policy_schema()
        properties = schema["properties"]

        assert "repo-name" in properties
        assert "repo_name" not in properties
        assert "python" in properties
        assert properties["python"]["type"] == "object"
        assert "branch-coverage" in properties["python"]["properties"]
        assert properties["repo-name"]["description"] == (
            "Repository name, usually as it appears in its hosting URL."
        )
        assert (
            properties["python"]["properties"]["branch-coverage"]["description"]
            == "Enable branch coverage in the Coverage.py pytest configuration."
        )
        assert properties["format"]["properties"]["tombi-errors-on-warnings"] == {
            "default": True,
            "description": "Make the Tombi lint hook fail when it emits warnings.",
            "title": "Tombi Errors On Warnings",
            "type": "boolean",
        }
        sorted_array_fields = (
            properties["github"]["properties"]["keep-workflow"],
            properties["nb"]["properties"]["excluded-dependencies"],
            properties["python"]["properties"]["type-checker"],
        )
        assert all(
            field["x-tombi-array-values-order"] == "ascending"
            for field in sorted_array_fields
        )
        assert properties["setup"]["properties"]["env"] == {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }
        assert schema["x-tombi-table-keys-order"] == "ascending"
        assert properties["format"]["x-tombi-table-keys-order"] == "ascending"

    def renders_stable_pretty_json() -> None:
        rendered = render_policy_schema()

        assert rendered.endswith("\n")
        assert '  "title": "ComPWA policy configuration"' in rendered
