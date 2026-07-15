"""``policy bootstrap`` — configure policy for an existing repository."""

from __future__ import annotations

from typing import TYPE_CHECKING

import rich

from compwa_policy.characterization import (
    RepositoryCharacterization,
    characterize_repository,
)
from compwa_policy.cli._settings import POLICY_TABLE
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.precommit import ModifiablePrecommit
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import ModifiablePyproject

if TYPE_CHECKING:
    from pathlib import Path

_POLICY_REPO = "https://github.com/ComPWA/policy"


def bootstrap() -> None:
    """Detect repository tooling, configure policy, and add its pre-commit hook."""
    characterization = characterize_repository()
    _write_policy_configuration(characterization)
    _add_check_dev_files_hook()
    rich.print(
        "[green]Bootstrapped policy configuration and the check-dev-files hook.[/green]"
    )


def _write_policy_configuration(
    characterization: RepositoryCharacterization,
) -> None:
    pyproject_path = CONFIG_PATH.pyproject
    pyproject = ModifiablePyproject.load(
        pyproject_path if pyproject_path.exists() else ""
    )
    with pyproject:
        policy = pyproject.get_table(POLICY_TABLE, create=True)
        policy["package-manager"] = characterization.package_manager
        type_checkers = sorted(characterization.type_checkers)
        if type_checkers:
            python_policy = pyproject.get_table(f"{POLICY_TABLE}.python", create=True)
            python_policy["type-checker"] = type_checkers
        elif not characterization.has_python_code:
            policy["python"] = False
        if not pyproject_path.exists():
            pyproject.dump(pyproject_path)
        pyproject.changelog.append("bootstrapped repository policy configuration")


def _add_check_dev_files_hook() -> None:
    precommit_path = CONFIG_PATH.precommit
    source: Path | str = precommit_path if precommit_path.exists() else "repos: []\n"
    precommit = ModifiablePrecommit.load(source)
    with precommit:
        precommit.update_single_hook_repo(
            Repo(
                repo=_POLICY_REPO,
                rev="",
                hooks=[Hook(id="check-dev-files")],
            )
        )
    if not precommit_path.exists():
        precommit.dump(precommit_path)
