from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from compwa_policy import self_check
from compwa_policy.cli._checks import CHECK_DEV_FILES_PATTERN
from compwa_policy.utilities.precommit import Precommit

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def describe_main() -> None:
    def accepts_the_central_check_dev_files_pattern(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        hook = _create_hook(CHECK_DEV_FILES_PATTERN)
        precommit, manifest = _write_configuration(tmp_path, hook)
        monkeypatch.chdir(tmp_path)

        assert self_check.main(precommit) == 0
        assert manifest.exists()

    def updates_a_pattern_that_drifted_in_both_yaml_files(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        hook = _create_hook(r"^wrong\.toml$")
        precommit, manifest = _write_configuration(tmp_path, hook)
        monkeypatch.chdir(tmp_path)

        assert self_check.main(precommit) == 0
        manifest_hook = yaml.safe_load(manifest.read_text())[0]
        assert manifest_hook["files"] == CHECK_DEV_FILES_PATTERN
        updated = Precommit.load(tmp_path / ".pre-commit-config.yaml")
        local_hook = updated.document["repos"][0]["hooks"][0]
        assert local_hook["files"] == CHECK_DEV_FILES_PATTERN

    def updates_a_local_hook_from_the_manifest(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        expected = _create_hook(CHECK_DEV_FILES_PATTERN)
        local = _create_hook(r"^wrong\.toml$")
        local["args"] = ["--no-github-actions"]
        precommit, _ = _write_configuration(
            tmp_path,
            local,
            manifest_hook=expected,
        )
        monkeypatch.chdir(tmp_path)

        assert self_check.main(precommit) == 0
        updated = Precommit.load(tmp_path / ".pre-commit-config.yaml")
        hook = updated.document["repos"][0]["hooks"][0]
        assert hook == {**expected, "args": ["--no-github-actions"]}

    def updates_the_precommit_test_fixture(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        expected = _create_hook(CHECK_DEV_FILES_PATTERN)
        precommit, _ = _write_configuration(tmp_path, expected)
        fixture_path = tmp_path / "tests/utilities/precommit/.pre-commit-config.yaml"
        fixture_path.parent.mkdir(parents=True)
        fixture_path.write_text(
            yaml.safe_dump(
                {
                    "repos": [
                        {
                            "repo": "https://github.com/ComPWA/policy",
                            "hooks": [
                                {
                                    "id": "check-dev-files",
                                    "args": ["--no-prettierrc"],
                                }
                            ],
                        }
                    ]
                },
                sort_keys=False,
            )
        )
        monkeypatch.chdir(tmp_path)

        assert self_check.main(precommit) == 0
        fixture = Precommit.load(fixture_path)
        hook = fixture.document["repos"][0]["hooks"][0]
        assert hook == {**expected, "args": ["--no-prettierrc"]}


def _create_hook(files: str) -> dict:
    return {
        "id": "check-dev-files",
        "name": "Check developer config files in the repository",
        "entry": "check-dev-files",
        "language": "python",
        "files": files,
        "pass_filenames": False,
    }


def _write_configuration(
    tmp_path: Path,
    hook: dict,
    *,
    manifest_hook: dict | None = None,
) -> tuple[Precommit, Path]:
    manifest = tmp_path / ".pre-commit-hooks.yaml"
    manifest.write_text(yaml.safe_dump([manifest_hook or hook], sort_keys=False))
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text(
        yaml.safe_dump({"repos": [{"repo": "local", "hooks": [hook]}]}, sort_keys=False)
    )
    return Precommit.load(config), manifest
