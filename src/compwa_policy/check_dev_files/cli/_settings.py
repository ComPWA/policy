"""Layered configuration for the :program:`policy` command.

A repository can declare its options once in a ``[tool.compwa.policy]`` table in
:code:`pyproject.toml` instead of repeating them under ``args:`` in every
``.pre-commit-config.yaml``. Options are resolved with this precedence (first match
wins):

1. the option explicitly passed on the command line (e.g. under ``args:``);
2. the ``[tool.compwa.policy]`` table in the repository's :code:`pyproject.toml`;
3. the built-in field default.

The table is organized hierarchically, mirroring the subcommand tree: shared options
live in the top-level table, while options that belong to a single subcommand live in a
sub-table named after it (``python``, ``github``, ``nb``, ``format``, ``repo``, and
``setup`` for the :program:`policy env` command). Environment variables are a plain
nested table under ``[tool.compwa.policy.setup.env]``:

.. code-block:: toml

    [tool.compwa.policy]
    dev-python-version = "3.13"
    package-manager = "pixi"

    [tool.compwa.policy.python]
    imports-on-top = true
    type-checker = ["mypy", "pyright"]

    [tool.compwa.policy.setup.env]
    PYTHONHASHSEED = "0"

Both the native TOML form (arrays, tables, booleans) and the legacy command-line string
form (``"mypy,pyright"``, ``"A=1,B=2"``) are accepted, so an ``args:`` list can be moved
into :code:`pyproject.toml` verbatim.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from compwa_policy.check_dev_files import _to_list
from compwa_policy.config import DEFAULT_DEV_PYTHON_VERSION
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject

#: Top-level table that holds the policy configuration in :code:`pyproject.toml`.
POLICY_TABLE = "tool.compwa.policy"
#: Sub-tables that group the options of a single subcommand. The :program:`policy env`
#: command maps to ``setup`` so that its ``environment-variables`` option can live in a
#: dedicated ``setup.env`` table instead of an awkward inline table.
_SUBCOMMAND_TABLES = ("python", "github", "nb", "format", "repo", "setup")


def _normalize_key(key: str) -> str:
    return key.replace("-", "_")


def _read_policy_config() -> dict[str, Any]:
    """Flatten the ``[tool.compwa.policy]`` tables into option keyword arguments.

    The top-level table and every subcommand sub-table are merged into a single flat
    mapping (since each option is owned by exactly one table, this cannot collide), with
    keys normalized from ``kebab-case`` to ``snake_case``. The environment-variable
    table ``[tool.compwa.policy.setup.env]`` is folded into the ``environment_variables``
    option.
    """
    if not CONFIG_PATH.pyproject.exists():
        return {}
    root = Pyproject.load().get_table(POLICY_TABLE, fallback={})
    flattened: dict[str, Any] = {}
    for key, value in root.items():
        if key not in _SUBCOMMAND_TABLES:
            flattened[_normalize_key(key)] = value
    for table in _SUBCOMMAND_TABLES:
        sub_table = root.get(table)
        if isinstance(sub_table, Mapping):
            for key, value in sub_table.items():
                if not (table == "setup" and key == "env"):
                    flattened[_normalize_key(key)] = value
    setup = root.get("setup", {})
    environment_variables = setup.get("env") if isinstance(setup, Mapping) else None
    if isinstance(environment_variables, Mapping):
        flattened["environment_variables"] = dict(environment_variables)
    return flattened


def _join(values: Any) -> str:
    if isinstance(values, str):
        return values
    if isinstance(values, Mapping):
        return ",".join(f"{key}={value}" for key, value in values.items())
    if isinstance(values, (list, tuple, set)):
        return ",".join(str(value) for value in values)
    return str(values)


class Settings(BaseSettings):
    """Resolved :program:`policy` options, layering the CLI over :code:`pyproject.toml`.

    Sources are restricted to the command line and ``[tool.compwa.policy]``: no
    environment variables or user-level files, keeping the configuration committed to the
    repository and reviewable.
    """

    model_config = SettingsConfigDict(extra="forbid")

    python: bool | None = None
    dev_python_version: str = DEFAULT_DEV_PYTHON_VERSION
    package_manager: str = "uv"
    repo_name: str = ""
    repo_organization: str = "ComPWA"
    repo_title: str = ""
    environment_variables: str = ""
    excluded_python_versions: str = ""
    no_ruff: bool = False
    imports_on_top: bool = False
    type_checker: list[str] = []
    keep_local_precommit: bool = False
    pytest_single_threaded: bool = False
    allow_vscode_coverage_gutters: bool = False
    allow_labels: bool = False
    allow_deprecated_workflows: bool = False
    no_github_actions: bool = False
    github_pages: bool = False
    keep_pr_linting: bool = False
    macos_python_version: str = "3.10"
    no_cd: bool = False
    no_milestones: bool = False
    no_pypi: bool = False
    no_version_branches: bool = False
    ci_skipped_tests: str = ""
    doc_apt_packages: str = ""
    keep_workflow: list[str] = []
    upgrade_frequency: str = "quarterly"
    no_binder: bool = False
    allowed_cell_metadata: str = ""
    no_cspell_update: bool = False
    gitpod: bool = False
    keep_contributing_md: bool = False
    keep_issue_templates: bool = False

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Restrict the configuration to the values passed to :func:`load_settings`.

        Dropping the environment and dotenv/secret-file sources keeps policy
        configuration committed to :file:`pyproject.toml` and reviewable, instead of
        leaking in from the surrounding shell.
        """
        del settings_cls, env_settings, dotenv_settings, file_secret_settings
        return (init_settings,)

    @field_validator("environment_variables", mode="before")
    @classmethod
    def _normalize_environment_variables(cls, value: Any) -> str:
        """Accept a string ``"A=1,B=2"`` or a ``{A = 1, B = 2}`` table.

        >>> Settings(environment_variables={"A": "1"}).environment_variables
        'A=1'
        >>> Settings(environment_variables="A=1, B=2").environment_variables
        'A=1, B=2'
        """
        if isinstance(value, Mapping):
            return _join(value)
        return value

    @field_validator(
        "ci_skipped_tests",
        "doc_apt_packages",
        "allowed_cell_metadata",
        "excluded_python_versions",
        mode="before",
    )
    @classmethod
    def _normalize_string_list(cls, value: Any) -> str:
        """Accept a comma/space string or a TOML array for a list-valued option.

        >>> Settings(excluded_python_versions=["3.6", "3.7"]).excluded_python_versions
        '3.6,3.7'
        >>> Settings(excluded_python_versions="3.6, 3.7").excluded_python_versions
        '3.6, 3.7'
        """
        return _join(value)

    @field_validator("type_checker", "keep_workflow", mode="before")
    @classmethod
    def _normalize_list(cls, value: Any) -> list[str]:
        """Accept a comma/space string, a TOML array, or repeated CLI options.

        >>> Settings(type_checker="mypy, pyright").type_checker
        ['mypy', 'pyright']
        >>> Settings(type_checker=["mypy", "pyright"]).type_checker
        ['mypy', 'pyright']
        """
        if isinstance(value, str):
            return _to_list(value)
        return [item.value if isinstance(item, Enum) else str(item) for item in value]


def load_settings(**cli_overrides: Any) -> Settings:
    """Resolve :program:`policy` options from the CLI and :code:`pyproject.toml`.

    Command-line options that were not explicitly passed are dropped (they arrive as
    ``None``), so they do not shadow a value set in the ``[tool.compwa.policy]`` table.
    The remaining options are layered over the ``[tool.compwa.policy]`` table, which in
    turn falls back to the built-in field defaults.
    """
    cli = {key: value for key, value in cli_overrides.items() if value is not None}
    return Settings(**{**_read_policy_config(), **cli})
