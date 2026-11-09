from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import ValidationError

from compwa_policy.cli._schema import create_policy_schema, render_policy_schema
from compwa_policy.cli._settings import load_settings


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

    def orders_properties_alphabetically() -> None:
        properties = create_policy_schema()["properties"]
        assert list(properties) == sorted(properties)
        assert all(
            list(section["properties"]) == sorted(section["properties"])
            for section in properties.values()
            if section.get("type") == "object" and "properties" in section
        )

    def renders_stable_pretty_json() -> None:
        rendered = render_policy_schema()

        assert rendered.endswith("\n")
        assert '  "title": "ComPWA policy configuration"' in rendered

    @pytest.mark.parametrize(
        ("option", "alias"),
        [("macos-runner", "MacosRunnerLabel"), ("ubuntu-runner", "UbuntuRunnerLabel")],
    )
    def references_named_runner_definitions(option: str, alias: str) -> None:
        schema = create_policy_schema()
        field = schema["properties"]["github"]["properties"][option]
        assert field["anyOf"] == [{"$ref": f"#/$defs/{alias}"}, {"type": "null"}]
        assert schema["$defs"][alias]["type"] == "string"
        assert schema["$defs"][alias]["enum"]


def describe_runner_labels() -> None:
    @pytest.mark.parametrize(
        ("option", "value"),
        [
            ("macos-runner", "ubuntu-26.04"),
            ("ubuntu-runner", "macos-26"),
            ("macos-runner", ""),
            ("ubuntu-runner", ""),
        ],
        ids=[
            "wrong-macos-platform",
            "wrong-ubuntu-platform",
            "empty-macos",
            "empty-ubuntu",
        ],
    )
    def rejects_invalid_runner_labels(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, option: str, value: str
    ) -> None:

        monkeypatch.chdir(tmp_path)
        content = dedent(f"""
            [tool.compwa.policy.github]
            {option} = "{value}"
        """)
        (tmp_path / "pyproject.toml").write_text(content)
        with pytest.raises(ValidationError, match=option.replace("-", "_")):
            load_settings()

    def accepts_explicit_and_default_labels(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        monkeypatch.chdir(tmp_path)
        content = dedent("""
            [tool.compwa.policy.github]
            macos-runner = "macos-26-intel"
        """)
        (tmp_path / "pyproject.toml").write_text(content)
        settings = load_settings()
        assert settings.macos_runner == "macos-26-intel"
        assert settings.ubuntu_runner is None

    def defaults_to_no_overrides(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[tool.compwa.policy.github]\n")
        settings = load_settings()
        assert settings.macos_runner is None
        assert settings.ubuntu_runner is None
