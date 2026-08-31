from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from compwa_policy.github.release_drafter import _get_expected_config

if TYPE_CHECKING:
    from pathlib import Path


def describe_get_expected_config() -> None:
    @pytest.mark.parametrize(
        ("tag_prefix", "expected_version"),
        [("", "$NEXT_PATCH_VERSION"), ("v", "v$NEXT_PATCH_VERSION")],
        ids=["default", "prefixed"],
    )
    def applies_tag_prefix_to_tag_refs(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        tag_prefix: str,
        expected_version: str,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".readthedocs.yml").touch()

        config = _get_expected_config("actions", "ComPWA actions", "ComPWA", tag_prefix)

        assert config["name-template"] == ("ComPWA actions $NEXT_PATCH_VERSION")
        assert config["tag-template"] == expected_version
        # cspell:ignore rtfd
        assert "actions.rtfd.io/en/$NEXT_PATCH_VERSION" in config["template"]
        assert (
            f"ComPWA/actions/compare/$PREVIOUS_TAG...{expected_version}"
            in config["template"]
        )
