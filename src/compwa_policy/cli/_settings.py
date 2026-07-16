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
from typing import Annotated, Any, TypeVar

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from compwa_policy import TomlFormatter, _to_list
from compwa_policy.config import (
    DEFAULT_DEV_PYTHON_VERSION,
    PackageManagerChoice,
    PythonVersion,
    TypeChecker,
    UpgradeFrequency,
)
from compwa_policy.utilities import CONFIG_PATH
from compwa_policy.utilities.pyproject import Pyproject

T = TypeVar("T")
SortedArray = Annotated[
    list[T],
    Field(json_schema_extra={"x-tombi-array-values-order": "ascending"}),
]
"""Array-valued setting whose TOML representation is sorted by Tombi."""

#: Top-level table that holds the policy configuration in :code:`pyproject.toml`.
POLICY_TABLE = "tool.compwa.policy"
#: Sub-tables that group the options of a single subcommand. The :program:`policy env`
#: command maps to ``setup`` so that its ``environment-variables`` option can live in a
#: dedicated ``setup.env`` table instead of an awkward inline table.
_SUBCOMMAND_TABLES = ("python", "github", "nb", "format", "repo", "setup")

#: Options that belong to a single subcommand and therefore live in its sub-table. Every
#: option not listed here is shared by several subcommands and lives in the top-level
#: ``[tool.compwa.policy]`` table; ``environment_variables`` is the exception that becomes
#: a nested ``setup.env`` table (see :func:`policy_sub_table`).
_SCOPED_OPTIONS: dict[str, frozenset[str]] = {
    "python": frozenset({
        "allow_vscode_coverage_gutters",
        "branch_coverage",
        "excluded_python_versions",
        "imports_on_top",
        "type_checker",
    }),
    "github": frozenset({
        "allow_deprecated_workflows",
        "allow_labels",
        "ci_skipped_tests",
        "github_pages",
        "keep_pr_linting",
        "keep_workflow",
        "macos_python_version",
        "no_cd",
        "no_github_actions",
        "no_milestones",
        "no_pypi",
        "no_version_branches",
        "upgrade_frequency",
    }),
    "nb": frozenset({
        "allowed_cell_metadata",
        "excluded_dependencies",
        "no_binder",
    }),
    "format": frozenset({
        "no_cspell_update",
        "tombi_errors_on_warnings",
        "toml_formatter",
    }),
    "repo": frozenset({"gitpod", "keep_issue_templates"}),
    "setup": frozenset({"keep_contributing_md"}),
}


def _normalize_key(key: str) -> str:
    return key.replace("-", "_")


def policy_sub_table(field_name: str) -> str | None:
    """Return the ``[tool.compwa.policy.*]`` sub-table that owns *field_name*.

    Returns `None` for options that are shared by several subcommands and therefore live
    in the top-level ``[tool.compwa.policy]`` table.

    >>> policy_sub_table("type_checker")
    'python'
    >>> policy_sub_table("keep_contributing_md")
    'setup'
    >>> policy_sub_table("dev_python_version") is None
    True
    """
    for sub_table, fields in _SCOPED_OPTIONS.items():
        if field_name in fields:
            return sub_table
    return None


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
    """Render a value as the legacy comma-separated command-line string.

    >>> _join("3.6, 3.7")
    '3.6, 3.7'
    >>> _join(["3.6", "3.7"])
    '3.6,3.7'
    >>> _join({"A": "1", "B": "2"})
    'A=1,B=2'
    >>> _join(3)
    '3'
    """
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

    model_config = SettingsConfigDict(extra="forbid", use_attribute_docstrings=True)

    python: bool | None = None
    """Whether the repository contains Python code; ``None`` enables auto-detection."""
    dev_python_version: PythonVersion = DEFAULT_DEV_PYTHON_VERSION
    """Python version used for the development environment."""
    package_manager: PackageManagerChoice = "uv"
    """Package or environment manager used by the repository."""
    repo_name: str = ""
    """Repository name, usually as it appears in its hosting URL."""
    repo_organization: str = "ComPWA"
    """Organization under which the repository is hosted."""
    repo_title: str = ""
    """Human-readable repository title; defaults to the repository name when empty."""
    environment_variables: str = ""
    """Environment variables added to the development setup."""
    excluded_python_versions: str = ""
    """Python versions that the project does not support."""
    excluded_dependencies: SortedArray[str] = []
    """Notebook dependencies that policy must not install."""
    no_ruff: bool = False
    """Do not enforce Ruff as a linter."""
    imports_on_top: bool = False
    """Move notebook imports to the top of the notebook."""
    branch_coverage: bool = True
    """Enable branch coverage in the Coverage.py pytest configuration."""
    type_checker: SortedArray[TypeChecker] = []
    """Type checkers used by the project."""
    pytest_single_threaded: bool = False
    """Run pytest without the parallel ``-n`` argument."""
    allow_vscode_coverage_gutters: bool = False
    """Keep and recommend the VS Code Coverage Gutters extension."""
    allow_labels: bool = False
    """Do not enforce the shared ``labels.toml`` configuration."""
    allow_deprecated_workflows: bool = False
    """Allow deprecated continuous-integration workflows."""
    no_github_actions: bool = False
    """Do not add the standard ComPWA GitHub Actions workflows."""
    github_pages: bool = False
    """Publish the documentation through GitHub Pages."""
    keep_pr_linting: bool = False
    """Do not overwrite the pull-request linting workflow."""
    macos_python_version: str = "3.10"
    """Python version for the macOS test job; use ``disable`` to omit the job."""
    no_cd: bool = False
    """Do not add continuous-deployment workflows."""
    no_milestones: bool = False
    """Do not add workflows that manage GitHub milestones."""
    no_pypi: bool = False
    """Do not publish the package to PyPI."""
    no_version_branches: bool = False
    """Do not update major and minor version branches when tagging a release."""
    ci_skipped_tests: str = ""
    """Python versions for which the CI test job is skipped."""
    doc_apt_packages: str = ""
    """APT packages required to build the documentation."""
    keep_workflow: SortedArray[str] = []
    """GitHub Actions workflow files that policy must not update or remove."""
    upgrade_frequency: UpgradeFrequency = "quarterly"
    """Frequency of the workflow that upgrades lock and constraint files."""
    no_binder: bool = False
    """Do not update the Binder configuration."""
    allowed_cell_metadata: str = ""
    """Metadata keys allowed in Jupyter notebook cells."""
    no_cspell_update: bool = False
    """Do not enforce the shared cSpell configuration."""
    tombi_errors_on_warnings: bool = True
    """Make the Tombi lint hook fail when it emits warnings."""
    toml_formatter: TomlFormatter = "tombi"
    """TOML formatter configured for the repository."""
    gitpod: bool = False
    """Create and maintain a Gitpod configuration file."""
    keep_contributing_md: bool = False
    """Do not update or remove ``CONTRIBUTING.md``."""
    keep_issue_templates: bool = False
    """Do not remove the GitHub issue-template directory."""

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

    @field_validator(
        "excluded_dependencies",
        "type_checker",
        "keep_workflow",
        mode="before",
    )
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
