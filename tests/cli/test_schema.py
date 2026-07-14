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
        assert properties["setup"]["properties"]["env"] == {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }

    def renders_stable_pretty_json() -> None:
        rendered = render_policy_schema()

        assert rendered.endswith("\n")
        assert '  "title": "ComPWA policy configuration"' in rendered
