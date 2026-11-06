import json
from pathlib import Path

import pytest

from compwa_policy.utilities.session import Session
from compwa_policy.utilities.vscode import ModifiableVscodeSettings, update_settings


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        (
            {
                "[json]": {
                    "editor.defaultFormatter": "prettier",
                    "editor.wordWrap": "on",
                },
                "[css]": {"editor.defaultFormatter": "prettier"},
                "editor.formatOnSave": True,
            },
            {
                "[css][json]": {"editor.defaultFormatter": "prettier"},
                "[json]": {"editor.wordWrap": "on"},
                "editor.formatOnSave": True,
            },
        ),
        (
            {
                "[json][css]": {"editor.defaultFormatter": "prettier"},
                "[css]": {"editor.defaultFormatter": "prettier"},
                "[python]": {"editor.defaultFormatter": "ruff"},
            },
            {
                "[css][json]": {"editor.defaultFormatter": "prettier"},
                "[python]": {"editor.defaultFormatter": "ruff"},
            },
        ),
        (
            {
                "[json][css]": {"editor.defaultFormatter": "prettier"},
                "[json]": {"editor.defaultFormatter": "other"},
            },
            {
                "[json][css]": {"editor.defaultFormatter": "prettier"},
                "[json]": {"editor.defaultFormatter": "other"},
            },
        ),
        (
            {
                "[css][json]": {"editor.wordWrap": "on"},
                "[css]": {"editor.defaultFormatter": "prettier"},
                "[json]": {"editor.defaultFormatter": "prettier"},
            },
            {
                "[css][json]": {
                    "editor.wordWrap": "on",
                    "editor.defaultFormatter": "prettier",
                },
            },
        ),
        (
            {
                "[css][json]": {"editor.defaultFormatter": "prettier"},
                "[json]": {"editor.defaultFormatter": None},
                "files.associations": {"*.foo": "json"},
                "[invalid]suffix": {"editor.defaultFormatter": "prettier"},
            },
            {
                "[css][json]": {"editor.defaultFormatter": "prettier"},
                "[json]": {"editor.defaultFormatter": None},
                "files.associations": {"*.foo": "json"},
                "[invalid]suffix": {"editor.defaultFormatter": "prettier"},
            },
        ),
    ],
    ids=[
        "json-overrides",
        "existing-group",
        "conflict",
        "selector-collision",
        "null-and-unrelated",
    ],
)
def describe_consolidate_formatters(original: dict, expected: dict):
    def preserves_settings_and_is_idempotent(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        path = Path(".vscode/settings.json")
        path.parent.mkdir()
        path.write_text(json.dumps(original))
        with Session() as session:
            settings = session.get(ModifiableVscodeSettings)
            assert settings.changed == (original != expected)
            session.flush()
        assert json.loads(path.read_text()) == expected
        before = path.read_bytes()
        with Session() as session:
            session.get(ModifiableVscodeSettings)
            assert session.flush() == []
        assert path.read_bytes() == before


def describe_formatter_updates():
    def ignores_recreated_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        path = Path(".vscode/settings.json")
        path.parent.mkdir()
        original = {
            "[css][json]": {"editor.defaultFormatter": "prettier"},
            "[json]": {"editor.wordWrap": "on"},
        }
        path.write_text(json.dumps(original))
        with Session() as session:
            update_settings(
                session, {"[json]": {"editor.defaultFormatter": "prettier"}}
            )
            update_settings(session, {"[css]": {"editor.defaultFormatter": "prettier"}})
            assert session.flush() == []
        assert json.loads(path.read_text()) == original

    def reports_other_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        path = Path(".vscode/settings.json")
        path.parent.mkdir()
        path.write_text(
            json.dumps({"[css][json]": {"editor.defaultFormatter": "prettier"}})
        )
        with Session() as session:
            update_settings(
                session,
                {
                    "[json]": {
                        "editor.defaultFormatter": "prettier",
                        "editor.wordWrap": "on",
                    }
                },
            )
            assert session.flush() == ["Updated VS Code settings"]
        assert json.loads(path.read_text()) == {
            "[css][json]": {"editor.defaultFormatter": "prettier"},
            "[json]": {"editor.wordWrap": "on"},
        }
