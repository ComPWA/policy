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

        config = _get_expected_config(
            repo_name="actions",
            repo_title="ComPWA actions",
            organization="ComPWA",
            release_name_template="{{ REPO_TITLE }} $NEXT_PATCH_VERSION",
            tag_prefix=tag_prefix,
        )

        assert config["name-template"] == ("ComPWA actions $NEXT_PATCH_VERSION")
        assert config["tag-template"] == expected_version
        assert "actions.rtfd.io/en/$NEXT_PATCH_VERSION" in config["template"]
        assert (
            f"ComPWA/actions/compare/$PREVIOUS_TAG...{expected_version}"
            in config["template"]
        )

    def omits_documentation_link_without_readthedocs(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config = _get_expected_config(
            repo_name="actions",
            repo_title="ComPWA actions",
            organization="ComPWA",
            release_name_template="{{ REPO_TITLE }} $NEXT_PATCH_VERSION",
            tag_prefix="v",
        )
        assert "rtfd.io" not in config["template"]

    def renders_configured_release_name_template() -> None:
        config = _get_expected_config(
            repo_name="actions",
            repo_title="ComPWA actions",
            organization="ComPWA",
            release_name_template=(
                "{{ ORGANIZATION }}/{{ REPO_NAME }}@{{ TAG_PREFIX }}$NEXT_PATCH_VERSION"
            ),
            tag_prefix="v",
        )

        assert config["name-template"] == "ComPWA/actions@v$NEXT_PATCH_VERSION"
