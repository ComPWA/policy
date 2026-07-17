from pathlib import Path

import pytest
import rtoml
import yaml

from compwa_policy.cli.bootstrap import bootstrap


def describe_bootstrap():
    def creates_policy_configuration_and_precommit_hook(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        git_init(tmp_path)
        (tmp_path / "package.py").write_text("value = 1\n")
        (tmp_path / "uv.lock").touch()
        (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")

        bootstrap()

        document = rtoml.load(tmp_path / "pyproject.toml")
        policy = document["tool"]["compwa"]["policy"]
        assert policy["package-manager"] == "uv"
        assert policy["python"]["type-checker"] == ["mypy"]
        precommit = yaml.safe_load((tmp_path / ".pre-commit-config.yaml").read_text())
        policy_repo = precommit["repos"][0]
        assert policy_repo["repo"] == "https://github.com/ComPWA/policy"
        assert policy_repo["hooks"] == [{"id": "check-dev-files"}]

    def preserves_existing_precommit_hooks(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        git_init,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        git_init(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n  - repo: meta\n    hooks:\n      - id: check-hooks-apply\n"
        )

        bootstrap()

        precommit = yaml.safe_load((tmp_path / ".pre-commit-config.yaml").read_text())
        hook_ids = {hook["id"] for repo in precommit["repos"] for hook in repo["hooks"]}
        assert hook_ids == {"check-dev-files", "check-hooks-apply"}
