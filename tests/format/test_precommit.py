from __future__ import annotations

import io

import yaml

from compwa_policy.errors import PrecommitError
from compwa_policy.format import precommit
from compwa_policy.utilities.precommit import ModifiablePrecommit

_CONFIG_WITH_NOTEBOOK_HOOK = """\
repos:
  - repo: https://github.com/ComPWA/policy
    rev: 0.1.0
    hooks:
      - id: check-dev-files
      - id: set-nb-cells
        args: [--add-install-cell]
"""

_POLICY_URL = "https://github.com/ComPWA/policy"
_NBHOOKS_URL = "https://github.com/ComPWA/nbhooks"


def _run(config: str, *, has_notebooks: bool) -> tuple[bool, str]:
    """Run the migration and report whether it changed anything and the result.

    Tags cannot be fetched (the ``_offline_git_ls_remote`` fixture), so the new
    ComPWA/nbhooks repo entry is pinned to the fallback revision ``PLEASE-UPDATE``.
    """
    stream = io.StringIO(config)
    changed = False
    try:
        with ModifiablePrecommit.load(stream) as pc:
            precommit._update_notebook_hooks(pc, has_notebooks=has_notebooks)
    except PrecommitError:
        changed = True
    return changed, stream.getvalue()


def test_migrates_notebook_hooks_to_nbhooks():
    changed, result = _run(_CONFIG_WITH_NOTEBOOK_HOOK, has_notebooks=True)
    assert changed
    repos = {repo["repo"]: repo for repo in yaml.safe_load(result)["repos"]}

    policy_hook_ids = {hook["id"] for hook in repos[_POLICY_URL]["hooks"]}
    assert policy_hook_ids == {"check-dev-files"}

    nbhooks = repos[_NBHOOKS_URL]
    assert nbhooks["rev"] == "PLEASE-UPDATE"
    nbhooks_ids = {hook["id"] for hook in nbhooks["hooks"]}
    assert nbhooks_ids == {
        "remove-empty-tags",
        "set-nb-cells",
        "set-nb-display-name",
        "strip-nb-whitespace",
    }
    set_nb_cells = next(h for h in nbhooks["hooks"] if h["id"] == "set-nb-cells")
    assert set_nb_cells["args"] == ["--add-install-cell"], "args must be preserved"


def test_migration_is_idempotent():
    _, migrated = _run(_CONFIG_WITH_NOTEBOOK_HOOK, has_notebooks=True)
    changed, _ = _run(migrated, has_notebooks=True)
    assert not changed


def test_no_notebooks_only_migrates_existing_hooks():
    changed, result = _run(_CONFIG_WITH_NOTEBOOK_HOOK, has_notebooks=False)
    assert changed
    repos = {repo["repo"]: repo for repo in yaml.safe_load(result)["repos"]}
    nbhooks_ids = {hook["id"] for hook in repos[_NBHOOKS_URL]["hooks"]}
    assert nbhooks_ids == {"set-nb-cells"}, "no defaults added without notebooks"
