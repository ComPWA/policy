"""Check `Ruff <https://docs.astral.sh/ruff>`_ configuration."""

from __future__ import annotations

import os
from collections import abc
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML
from setuptools import find_packages

from compwa_policy.utilities import CONFIG_PATH, natural_sorting, remove_configs, vscode
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.precommit.struct import Hook, Repo
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    complies_with_subset,
    has_dependency,
    has_pyproject_package_name,
)
from compwa_policy.utilities.readme import add_badge, remove_badge
from compwa_policy.utilities.toml import to_toml_array
from compwa_policy.utilities.yaml import read_preserved_yaml

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from tomlkit.items import Array

    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.precommit import ModifiablePrecommit
    from compwa_policy.utilities.session import Session


@check_hook(
    group="python",
    paths=[
        CONFIG_PATH.precommit,
        CONFIG_PATH.pyproject,
        CONFIG_PATH.readme,
        CONFIG_PATH.vscode_extensions,
        CONFIG_PATH.vscode_settings,
        ".flake8",
        ".pydocstyle",
        ".pylintrc",
        "docs/.pydocstyle",
        "tests/.pydocstyle",
    ],
    enabled=lambda args, ctx: ctx.is_python_repo and (not args.no_ruff),
)
def check(session: Session, args: Arguments, ctx: CheckContext) -> None:
    has_notebooks = ctx.has_notebooks
    imports_on_top = args.imports_on_top
    precommit = session.precommit
    config = session.pyproject
    if config is None:
        return
    add_badge(
        session,
        "[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)",
    )
    config.remove_dependency("radon")
    _remove_black(session)
    _remove_flake8(session)
    _remove_isort(session, imports_on_top)
    _remove_pydocstyle(session)
    _remove_pylint(session)
    _move_ruff_lint_config(config)
    if has_notebooks and imports_on_top:
        _sort_imports_on_top(precommit, config)
    _update_ruff_config(precommit, config, has_notebooks)
    _update_precommit_hook(precommit, has_notebooks)
    if not has_dependency(config, "ruff"):
        _update_lint_dependencies(session)
    _update_vscode_settings(session)


def _remove_black(session: Session, /) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return
    vscode.remove_extension_recommendation(
        session,
        "ms-python.black-formatter",
        unwanted=True,
    )
    __remove_tool_table(pyproject, "black")
    pyproject.remove_dependency("black", ignored_sections=["doc", "notebooks", "test"])
    remove_badge(session, badge_pattern=r".*https://github\.com/psf.*/black.*")
    precommit.remove_hook("black-jupyter")
    precommit.remove_hook("blacken-docs")
    vscode.remove_settings(session, ["black-formatter.importStrategy"])


def _remove_flake8(session: Session, /) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return
    remove_configs(session, [".flake8"])
    __remove_nbqa_option(pyproject, "flake8")
    pyproject.remove_dependency("flake8")
    pyproject.remove_dependency("pep8-naming")
    vscode.remove_extension_recommendation(session, "ms-python.flake8", unwanted=True)
    precommit.remove_hook("autoflake")  # cspell:ignore autoflake
    precommit.remove_hook("flake8")
    precommit.remove_hook("nbqa-flake8")
    vscode.remove_settings(session, ["flake8.importStrategy"])


def _remove_isort(session: Session, /, imports_on_top: bool) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return
    __remove_nbqa_option(pyproject, "black")
    vscode.remove_extension_recommendation(session, "ms-python.isort", unwanted=True)
    precommit.remove_hook("isort")
    if not imports_on_top:
        __remove_tool_table(pyproject, "isort")
        __remove_nbqa_option(pyproject, "isort")
        precommit.remove_hook("nbqa-isort")
    vscode.remove_settings(session, ["isort.check", "isort.importStrategy"])
    remove_badge(session, r".*https://img\.shields\.io/badge/%20imports\-isort")


def __remove_nbqa_option(pyproject: ModifiablePyproject, option: str) -> None:
    # cspell:ignore addopts
    table_key = "tool.nbqa.addopts"
    if not pyproject.has_table(table_key):
        return
    nbqa_table = pyproject.get_table(table_key)
    if option not in nbqa_table:
        return
    nbqa_table.pop(option)
    msg = f"Removed {option!r} nbQA options from [{table_key}]"
    pyproject.changelog.append(msg)


def __remove_tool_table(pyproject: ModifiablePyproject, tool_table: str) -> None:
    tools = pyproject._document.get("tool")  # noqa: SLF001
    if isinstance(tools, dict) and tool_table in tools:
        tools.pop(tool_table)
        msg = f"Removed [tool.{tool_table}] table"
        pyproject.changelog.append(msg)


def _remove_pydocstyle(session: Session, /) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return
    remove_configs(
        session,
        [
            ".pydocstyle",
            "docs/.pydocstyle",
            "tests/.pydocstyle",
        ],
    )
    pyproject.remove_dependency("pydocstyle")
    precommit.remove_hook("pydocstyle")


def _remove_pylint(session: Session, /) -> None:
    precommit = session.precommit
    pyproject = session.pyproject
    if pyproject is None:
        return
    remove_configs(session, [".pylintrc"])  # cspell:ignore pylintrc
    pyproject.remove_dependency("pylint")
    vscode.remove_extension_recommendation(session, "ms-python.pylint", unwanted=True)
    precommit.remove_hook("pylint")
    precommit.remove_hook("nbqa-pylint")
    vscode.remove_settings(session, ["pylint.importStrategy"])


def _move_ruff_lint_config(pyproject: ModifiablePyproject) -> None:
    """Migrate linting configuration to :code:`tool.ruff.lint`.

    See `this blog <https://astral.sh/blog/ruff-v0.2.0>`_ for details.
    """
    lint_option_keys = {
        "extend-select",
        "ignore",
        "isort",
        "pep8-naming",
        "per-file-ignores",
        "pydocstyle",
        "select",
        "task-tags",
    }
    global_settings = pyproject.get_table("tool.ruff", create=True)
    lint_settings = {k: v for k, v in global_settings.items() if k in lint_option_keys}
    lint_arrays = {
        k: v for k, v in lint_settings.items() if isinstance(v, abc.Sequence)
    }
    if lint_arrays:
        lint_config = pyproject.get_table("tool.ruff.lint", create=True)
        lint_config.update(lint_arrays)
    lint_tables = {k: v for k, v in lint_settings.items() if isinstance(v, abc.Mapping)}
    for table_name, values in lint_tables.items():
        lint_config = pyproject.get_table(f"tool.ruff.lint.{table_name}", create=True)
        lint_config.update(values)
    for key in lint_settings:
        del global_settings[key]
    if lint_arrays or lint_tables:
        pyproject.changelog.append("Moved linting configuration to [tool.ruff.lint]")


def _update_ruff_config(
    precommit: ModifiablePrecommit,
    pyproject: ModifiablePyproject,
    has_notebooks: bool,
) -> None:
    __update_global_settings(pyproject, has_notebooks)
    __update_ruff_format_settings(pyproject)
    __update_ruff_lint_settings(pyproject)
    __update_per_file_ignores(pyproject, has_notebooks)
    __remove_deprecated_rules(pyproject)
    if has_notebooks:
        __update_flake8_builtins(pyproject)
        __update_flake8_comprehensions_builtins(pyproject)
    __update_isort_settings(pyproject, has_notebooks)
    __update_pydocstyle_settings(pyproject)
    __remove_nbqa(precommit, pyproject)


def __update_global_settings(
    pyproject: ModifiablePyproject, has_notebooks: bool
) -> None:
    settings = pyproject.get_table("tool.ruff", create=True)
    minimal_settings: dict[str, Any] = {
        "preview": True,
        "show-fixes": True,
    }
    project = pyproject.get_table("project", create=True)
    if "requires-python" in project:
        if settings.get("target-version") is not None:
            settings.pop("target-version")
            msg = "Removed target-version from Ruff configuration"
            pyproject.changelog.append(msg)
    else:
        minimal_settings["target-version"] = ___get_target_version(pyproject)
    if has_notebooks:
        key = "extend-include"
        default_includes = sorted({
            "*.ipynb",
            *settings.get(key, []),
        })
        minimal_settings[key] = to_toml_array(default_includes)
    src_directories = ___get_src_directories()
    if src_directories:
        minimal_settings["src"] = src_directories
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        msg = "Updated Ruff configuration"
        pyproject.changelog.append(msg)


def ___get_target_version(pyproject: Pyproject) -> str:
    """Get minimal :code:`target-version` for Ruff.

    >>> pyproject = Pyproject.load()
    >>> ___get_target_version(pyproject)
    'py310'
    """
    supported_python_versions = pyproject.get_supported_python_versions()
    versions = {f"py{v.replace('.', '')}" for v in supported_python_versions}
    versions &= {"py37", "py38", "py39", "py310", "py311", "py312"}
    if not versions:
        return "py37"
    lowest_version, *_ = sorted(versions, key=natural_sorting)
    return lowest_version


def ___get_src_directories() -> list[str]:
    expected_directories = (
        "src",
        "tests",
    )
    directories = tuple(
        path
        for path in expected_directories
        if os.path.exists(path)
        if os.path.isdir(path)
    )
    return to_toml_array(sorted(directories))


def __update_ruff_format_settings(pyproject: ModifiablePyproject) -> None:
    settings = pyproject.get_table("tool.ruff.format", create=True)
    minimal_settings = {
        "docstring-code-format": True,
        "line-ending": "lf",
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        msg = "Updated Ruff formatter configuration"
        pyproject.changelog.append(msg)


def __update_ruff_lint_settings(pyproject: ModifiablePyproject) -> None:
    settings = pyproject.get_table("tool.ruff.lint", create=True)
    ignored_rules = {
        "ANN401",  # allow typing.Any
        "COM812",  # missing trailing comma
        "CPY001",  # don't add copyright
        "D101",  # class docstring
        "D102",  # method docstring
        "D103",  # function docstring
        "D105",  # magic method docstring
        "D107",  # init docstring
        "D203",  # conflicts with D211
        "D213",  # multi-line docstring should start at the second line
        "D407",  # missing dashed underline after section
        "D416",  # section name does not have to end with a colon
        "DOC",  # do not check undocumented exceptions
        "E501",  # line-width already handled by black
        "FURB101",  # do not enforce Path.read_text()
        "FURB103",  # do not enforce Path.write_text()
        "FURB140",  # do not enforce itertools.starmap
        "G004",  # allow f-string in logging
        "ISC001",  # conflicts with ruff formatter
        "PLW1514",  # allow missing encoding in open()
        "PT001",  # allow pytest.fixture without parentheses
        "PTH",  # do not enforce Path
        "RUF067",  # `__init__` module should only contain docstrings and re-exports
        "SIM108",  # allow if-else blocks
    }
    if "3.6" in pyproject.get_supported_python_versions():
        ignored_rules.add("UP036")
    ignored_rules = ___merge_rules(settings.get("ignore", []), ignored_rules)
    minimal_settings = {
        "select": to_toml_array(["ALL"]),
        "ignore": to_toml_array(sorted(ignored_rules), multiline=True),
        "task-tags": ___get_task_tags(settings),
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        msg = "Updated Ruff linting configuration"
        pyproject.changelog.append(msg)
    if "extend-select" in settings:
        del settings["extend-select"]
        msg = "Removed [tool.ruff.lint.extend-select] configuration"
        pyproject.changelog.append(msg)


def ___get_task_tags(ruff_settings: Mapping[str, Any]) -> Array:
    existing: set[str] = set(ruff_settings.get("task-tags", set()))
    expected = {
        "cspell",
    }
    return to_toml_array(sorted(existing | expected))


def __update_per_file_ignores(
    pyproject: ModifiablePyproject, has_notebooks: bool
) -> None:
    minimal_settings: dict[str, Array] = {}
    if has_notebooks:
        key = "*.ipynb"
        minimal_settings[key] = ___get_per_file_ignores(
            pyproject,
            key=key,
            expected_ignores={
                "ANN",  # global-statement
                "B018",  # useless-expression
                "C90",  # complex-structure
                "D",  # pydocstyle
                "E303",  # too many blank lines, specific for jupyterlab-lsp
                "E703",  # useless-semicolon
                "N806",  # non-lowercase-variable-in-function
                "N816",  # mixed-case-variable-in-global-scope
                "PLR09",  # complicated logic
                "PLR2004",  # magic-value-comparison
                "PLW0602",  # global-variable-not-assigned
                "PLW0603",  # global-statement
                "S101",  # `assert` detected
                "T20",  # print found
                "TC00",  # type-checking block
                *___get_existing_nbqa_ignores(pyproject),
            },
            banned_ignores={
                "F821",  # identify variables that are not defined
                "ISC003",  # explicit-string-concatenation
                "TCH00",  # https://astral.sh/blog/ruff-v0.8.0#new-error-codes-for-flake8-type-checking-rules
            },
        )
    docs_dir = "docs"
    if os.path.exists(docs_dir) and os.path.isdir(docs_dir):
        key = f"{docs_dir}/*"
        minimal_settings[key] = ___get_per_file_ignores(
            pyproject,
            key=key,
            expected_ignores={
                "INP001",  # implicit namespace package
                "S101",  # `assert` detected
                "S113",  # requests call without timeout
            },
        )
    conf_path = f"{docs_dir}/conf.py"
    if os.path.exists(conf_path):
        key = conf_path
        minimal_settings[key] = ___get_per_file_ignores(
            pyproject,
            key=key,
            expected_ignores={
                "D100",  # no module docstring
            },
        )
    if os.path.exists("setup.py"):
        minimal_settings["setup.py"] = to_toml_array(["D100"])
    for tests_dir in ["benchmarks", "tests"]:
        if not os.path.exists(tests_dir):
            continue
        if not os.path.isdir(tests_dir):
            continue
        key = f"{tests_dir}/*"
        minimal_settings[key] = ___get_per_file_ignores(
            pyproject,
            key=key,
            expected_ignores={
                "ANN",  # don't check missing types
                "D",  # no need for pydocstyle
                "FBT001",  # don't force booleans as keyword arguments
                "INP001",  # allow implicit-namespace-package
                "RUF069",  # float-equality-comparison
                "PLC2701",  # private module imports
                "PLR2004",  # magic-value-comparison
                "PLR6301",  # allow non-static method
                "S101",  # allow assert
                "SLF001",  # allow access to private members
                "T20",  # allow print and pprint
            },
        )
    per_file_ignores = pyproject.get_table(
        "tool.ruff.lint.per-file-ignores", create=True
    )
    minimal_settings = {k: v for k, v in minimal_settings.items() if v}
    if not complies_with_subset(per_file_ignores, minimal_settings):
        per_file_ignores.update(minimal_settings)
        msg = "Updated Ruff configuration"
        pyproject.changelog.append(msg)


def __remove_deprecated_rules(pyproject: ModifiablePyproject) -> None:
    # https://docs.astral.sh/ruff/rules
    deprecated_rules = {
        "ANN101",
        "ANN102",
        "E999",
        "PD901",
        "PGH001",
        "PGH002",
        "PLR1701",
        "PLR1706",
        "PT004",
        "PT005",
        "RUF011",
        "RUF035",
        "S320",
        "S410",
        "TRY200",
        "UP027",
        "UP038",
    }
    per_file_ignores = "tool.ruff.lint.per-file-ignores"
    keys_to_check = [("tool.ruff.lint", "ignore")]
    keys_to_check.extend(
        (per_file_ignores, key)
        for key in pyproject.get_table(per_file_ignores, fallback=[])
    )
    updated_tables = False
    for table_name, key in keys_to_check:
        if not pyproject.has_table(table_name):
            continue
        table = pyproject.get_table(table_name)
        if key not in table:
            continue
        rules: set[str] = set(table[key])
        if not rules & deprecated_rules:
            continue
        rules -= deprecated_rules
        if rules:
            table[key] = to_toml_array(sorted(rules))
        else:
            del table[key]
        updated_tables = True
    if updated_tables:
        msg = "Removed deprecated Ruff rules"
        pyproject.changelog.append(msg)


def ___get_per_file_ignores(
    pyproject: Pyproject,
    key: str,
    expected_ignores: set[str],
    banned_ignores: set[str] | None = None,
) -> Array:
    per_file_ignores = pyproject.get_table(
        "tool.ruff.lint.per-file-ignores", create=True
    )
    existing_ignores = per_file_ignores.get(key, [])
    expected_ignores = ___merge_rules(expected_ignores, existing_ignores)
    if banned_ignores is not None:
        expected_ignores = ___ban_rules(expected_ignores, banned_ignores)
    global_settings = pyproject.get_table("tool.ruff.lint", create=True)
    global_ignores = global_settings.get("ignore", [])
    expected_ignores = ___ban_rules(expected_ignores, global_ignores)
    return to_toml_array(sorted(expected_ignores))


def ___ban_rules(rules: Iterable[str], banned_rules: Iterable[str]) -> set[str]:
    """Extend Ruff rules with new rules and filter out redundant ones.

    >>> result = ___ban_rules(
    ...     ["C90", "B018", "D", "E402"],
    ...     banned_rules=["D10", "C", "E"],
    ... )
    >>> sorted(result)
    ['B018', 'D']
    """
    banned_set = tuple(banned_rules)
    return {rule for rule in rules if not any(rule.startswith(r) for r in banned_set)}


def ___merge_rules(*rule_sets: Iterable[str]) -> set[str]:
    """Extend Ruff rules with new rules and filter out redundant ones.

    >>> sorted(___merge_rules(["C90", "B018"], ["D10", "C"]))
    ['B018', 'C', 'D10']
    """
    merged_rules: set[str] = set()
    for rule_set in rule_sets:
        merged_rules |= set(rule_set)
    return {
        rule
        for rule in merged_rules
        if not any(rule != r and rule.startswith(r) for r in merged_rules)
    }


def ___get_existing_nbqa_ignores(pyproject: Pyproject) -> set[str]:
    nbqa_table = pyproject.get_table("tool.nbqa.addopts", create=True)
    if not nbqa_table:
        return set()
    ruff_rules: list[str] = nbqa_table.get("ruff", [])
    return {
        r.replace("--extend-ignore=", "")
        for r in ruff_rules
        if r.startswith("--extend-ignore=")
    }


def __update_flake8_builtins(pyproject: ModifiablePyproject) -> None:
    # cspell:ignore ignorelist
    ___update_ruff_lint_table(
        pyproject,
        table_name="flake8-builtins",
        minimal_settings={"builtins-ignorelist": ["display"]},
    )


def __update_flake8_comprehensions_builtins(pyproject: ModifiablePyproject) -> None:
    ___update_ruff_lint_table(
        pyproject,
        table_name="flake8-comprehensions",
        minimal_settings={
            "allow-dict-calls-with-keyword-arguments": True,
        },
    )


def __update_isort_settings(
    pyproject: ModifiablePyproject, has_notebooks: bool
) -> None:
    packages_names = [mod for mod in find_packages("src") if "." not in mod]
    minimal_settings: dict[str, Any] = {}
    if has_notebooks and packages_names:
        minimal_settings["known-first-party"] = packages_names
    minimal_settings["split-on-trailing-comma"] = False
    ___update_ruff_lint_table(pyproject, "isort", minimal_settings)


def __update_pydocstyle_settings(pyproject: ModifiablePyproject) -> None:
    ___update_ruff_lint_table(
        pyproject,
        table_name="pydocstyle",
        minimal_settings={"convention": "google"},
    )


def ___update_ruff_lint_table(
    pyproject: ModifiablePyproject, table_name: str, minimal_settings: dict[str, Any]
) -> None:
    settings = pyproject.get_table(f"tool.ruff.lint.{table_name}", create=True)
    minimal_settings = {
        key: to_toml_array({*value, *settings.get(key, [])})
        if isinstance(value, abc.Iterable) and not isinstance(value, str)
        else value
        for key, value in minimal_settings.items()
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        msg = f"Updated Ruff {table_name} settings"
        pyproject.changelog.append(msg)


def __remove_nbqa(
    precommit: ModifiablePrecommit,
    pyproject: ModifiablePyproject,
) -> None:
    ___remove_nbqa_settings(pyproject)
    precommit.remove_hook("nbqa-ruff")


def ___remove_nbqa_settings(pyproject: ModifiablePyproject) -> None:
    nbqa_addopts = pyproject.get_table("tool.nbqa.addopts", create=True)
    if "ruff" in nbqa_addopts:
        del nbqa_addopts["ruff"]
    if not nbqa_addopts:
        tool_table = pyproject.get_table("tool", create=True)
        del tool_table["nbqa"]
    if nbqa_addopts:
        msg = "Removed Ruff configuration for nbQA"
        pyproject.changelog.append(msg)


def _update_precommit_hook(precommit: ModifiablePrecommit, has_notebooks: bool) -> None:
    yaml = YAML(typ="rt")
    lint_hook = Hook(id="ruff-check", args=yaml.load("[--fix]"))
    format_hook = Hook(id="ruff-format")
    if has_notebooks:
        types_str = "[python, pyi, jupyter]"
        lint_hook["types_or"] = yaml.load(types_str)  # use twice to avoid YAML anchor
        format_hook["types_or"] = yaml.load(types_str)
    expected_repo = Repo(
        repo="https://github.com/astral-sh/ruff-pre-commit",
        rev="",
        hooks=[lint_hook, format_hook],
    )
    precommit.update_single_hook_repo(expected_repo)


def _sort_imports_on_top(
    precommit: ModifiablePrecommit, pyproject: ModifiablePyproject
) -> None:
    __add_isort_configuration(pyproject)
    __add_nbqa_isort_pre_commit(precommit)


def __add_isort_configuration(pyproject: ModifiablePyproject) -> None:
    isort_settings = pyproject.get_table("tool.isort", create=True)
    minimal_settings = dict(
        profile="black",
    )
    if not complies_with_subset(isort_settings, minimal_settings):
        isort_settings.update(minimal_settings)
        msg = "Made isort configuration compatible with Ruff"
        pyproject.changelog.append(msg)


def __add_nbqa_isort_pre_commit(precommit: ModifiablePrecommit) -> None:
    existing_repo = precommit.find_repo("https://github.com/nbQA-dev/nbQA")
    excludes = None
    if existing_repo is not None and existing_repo.get("hooks"):
        nbqa_hook_candidates = [
            h for h in existing_repo["hooks"] if h["id"] == "nbqa-isort"
        ]
        if nbqa_hook_candidates:
            nbqa_hook = nbqa_hook_candidates[0]
            excludes = nbqa_hook.get("exclude")
    expected_repo = Repo(
        repo="https://github.com/nbQA-dev/nbQA",
        rev="1.9.1",
        hooks=[Hook(id="nbqa-isort", args=read_preserved_yaml("[--float-to-top]"))],
    )
    if excludes is not None:
        expected_repo["hooks"][0]["exclude"] = excludes
    precommit.update_single_hook_repo(expected_repo)


def _update_lint_dependencies(session: Session, /) -> None:
    if not has_pyproject_package_name(session):
        return
    pyproject = session.pyproject
    if pyproject is None:
        return
    python_versions = pyproject.get_supported_python_versions()
    if "3.6" in python_versions:
        ruff = 'ruff; python_version >="3.7.0"'
    else:
        ruff = "ruff"
    pyproject.add_dependency(ruff, dependency_group="dev")
    pyproject.remove_dependency(ruff, ignored_sections=["dev"])


def _update_vscode_settings(session: Session, /) -> None:
    # cspell:ignore charliermarsh
    vscode.add_extension_recommendation(session, "charliermarsh.ruff")
    vscode.update_settings(
        session,
        {
            "notebook.codeActionsOnSave": {
                "notebook.source.organizeImports": "explicit"
            },
            "notebook.formatOnSave.enabled": True,
            "[python]": {
                "editor.codeActionsOnSave": {
                    "source.organizeImports": "explicit",
                },
                "editor.defaultFormatter": "charliermarsh.ruff",
            },
            "ruff.enable": True,
            "ruff.importStrategy": "fromEnvironment",
            "ruff.organizeImports": True,
        },
    )
