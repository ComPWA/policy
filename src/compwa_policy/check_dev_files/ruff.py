"""Check `Ruff <https://docs.astral.sh/ruff>`_ configuration."""

from __future__ import annotations

import os
from textwrap import dedent
from typing import TYPE_CHECKING, Iterable

from ruamel.yaml import YAML
from tomlkit.items import Array, Table

from compwa_policy.check_dev_files.setup_cfg import (
    has_pyproject_build_system,
    has_setup_cfg_build_system,
)
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, natural_sorting, remove_configs, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.precommit import (
    Hook,
    Repo,
    remove_precommit_hook,
    update_single_hook_precommit_repo,
)
from compwa_policy.utilities.project_info import (
    get_project_info,
    get_supported_python_versions,
    open_setup_cfg,
)
from compwa_policy.utilities.pyproject import (
    add_dependency,
    complies_with_subset,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)
from compwa_policy.utilities.readme import add_badge, remove_badge

if TYPE_CHECKING:
    from tomlkit.toml_document import TOMLDocument


def main(has_notebooks: bool) -> None:
    executor = Executor()
    executor(
        add_badge,
        "[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)",
    )
    executor(_check_setup_cfg)
    executor(___uninstall, "radon")
    executor(_remove_black)
    executor(_remove_flake8)
    executor(_remove_isort)
    executor(_remove_pydocstyle)
    executor(_remove_pylint)
    executor(_move_ruff_lint_config)
    executor(_update_ruff_config, has_notebooks)
    executor(_update_precommit_hook, has_notebooks)
    executor(_update_lint_dependencies)
    executor(_update_vscode_settings)
    executor.finalize()


def _check_setup_cfg() -> None:
    if not has_setup_cfg_build_system():
        return
    cfg = open_setup_cfg()
    extras_require = "options.extras_require"
    if not cfg.has_section(extras_require):
        msg = f"Please list ruff under a section [{extras_require}] in setup.cfg"
        raise PrecommitError(msg)
    msg = f"""\
        Section [{extras_require}] in setup.cfg should look like this:

        [{extras_require}]
        ...
        sty =
            ...
            ruff
            ...
        dev =
            ...
            %(sty)s
            ...
    """
    msg = dedent(msg).strip()
    for section in ("dev", "sty"):
        if cfg.has_option(extras_require, section):
            continue
        raise PrecommitError(msg)
    lint_section = cfg.get(extras_require, "sty")
    if not any("ruff" in line for line in lint_section.split("\n")):
        raise PrecommitError(msg)


def _remove_black() -> None:
    executor = Executor()
    executor(
        vscode.remove_extension_recommendation,
        "ms-python.black-formatter",
        unwanted=True,
    )
    executor(__remove_tool_table, "black")
    executor(___uninstall, "black", ignore=["doc", "jupyter", "test"])
    executor(remove_badge, r".*https://github\.com/psf.*/black.*")
    executor(remove_precommit_hook, "black-jupyter")
    executor(remove_precommit_hook, "black")
    executor(remove_precommit_hook, "blacken-docs")
    executor(vscode.remove_settings, ["black-formatter.importStrategy"])
    executor.finalize()


def _remove_flake8() -> None:
    executor = Executor()
    executor(remove_configs, [".flake8"])
    executor(__remove_nbqa_option, "flake8")
    executor(___uninstall, "flake8")
    executor(___uninstall, "pep8-naming")
    executor(vscode.remove_extension_recommendation, "ms-python.flake8", unwanted=True)
    executor(remove_precommit_hook, "autoflake")  # cspell:ignore autoflake
    executor(remove_precommit_hook, "flake8")
    executor(remove_precommit_hook, "nbqa-flake8")
    executor(vscode.remove_settings, ["flake8.importStrategy"])
    executor.finalize()


def _remove_isort() -> None:
    executor = Executor()
    executor(__remove_nbqa_option, "black")
    executor(__remove_nbqa_option, "isort")
    executor(__remove_tool_table, "isort")
    executor(vscode.remove_extension_recommendation, "ms-python.isort", unwanted=True)
    executor(remove_precommit_hook, "isort")
    executor(remove_precommit_hook, "nbqa-isort")
    executor(vscode.remove_settings, ["isort.check", "isort.importStrategy"])
    executor(remove_badge, r".*https://img\.shields\.io/badge/%20imports\-isort")
    executor.finalize()


def __remove_nbqa_option(option: str) -> None:
    pyproject = load_pyproject()
    # cspell:ignore addopts
    nbqa_table: Table = pyproject.get("tool", {}).get("nbqa", {}).get("addopts")
    if nbqa_table is None:
        return
    if nbqa_table.get(option) is None:
        return
    nbqa_table.remove(option)
    write_pyproject(pyproject)
    msg = f"Removed {option!r} nbQA options from {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def __remove_tool_table(tool_table: str) -> None:
    pyproject = load_pyproject()
    if pyproject.get("tool", {}).get(tool_table) is None:
        return
    pyproject["tool"].remove(tool_table)  # type: ignore[union-attr]
    write_pyproject(pyproject)
    msg = f"Removed [tool.{tool_table}] section from {CONFIG_PATH.pyproject}"
    raise PrecommitError(msg)


def _remove_pydocstyle() -> None:
    executor = Executor()
    executor(
        remove_configs,
        [
            ".pydocstyle",
            "docs/.pydocstyle",
            "tests/.pydocstyle",
        ],
    )
    executor(___uninstall, "pydocstyle")
    executor(remove_precommit_hook, "pydocstyle")
    executor.finalize()


def _remove_pylint() -> None:
    executor = Executor()
    executor(remove_configs, [".pylintrc"])  # cspell:ignore pylintrc
    executor(___uninstall, "pylint")
    executor(vscode.remove_extension_recommendation, "ms-python.pylint", unwanted=True)
    executor(remove_precommit_hook, "pylint")
    executor(remove_precommit_hook, "nbqa-pylint")
    executor(vscode.remove_settings, ["pylint.importStrategy"])
    executor.finalize()


def ___uninstall(package: str, ignore: Iterable[str] | None = None) -> None:
    ignored_sections = set() if ignore is None else set(ignore)
    ___uninstall_from_setup_cfg(package, ignored_sections)
    ___uninstall_from_pyproject_toml(package, ignored_sections)


def ___uninstall_from_setup_cfg(package: str, ignored_sections: set[str]) -> None:
    if not os.path.exists(CONFIG_PATH.setup_cfg):
        return
    cfg = open_setup_cfg()
    section = "options.extras_require"
    if not cfg.has_section(section):
        return
    extras_require = cfg[section]
    for option in extras_require:
        if option in ignored_sections:
            continue
        if package not in cfg.get(section, option, raw=True):
            continue
        msg = f'Please remove {package} from the "{section}" section of setup.cfg'
        raise PrecommitError(msg)


def ___uninstall_from_pyproject_toml(package: str, ignored_sections: set[str]) -> None:  # noqa: C901
    if not os.path.exists(CONFIG_PATH.pyproject):
        return
    pyproject = load_pyproject()
    project = pyproject.get("project")
    if project is None:
        return
    updated = False
    dependencies = project.get("dependencies")
    if dependencies is not None and package in dependencies:
        dependencies.remove(package)
        updated = True
    optional_dependencies = project.get("optional-dependencies")
    if optional_dependencies is not None:
        for section, values in optional_dependencies.items():
            if section in ignored_sections:
                continue
            if package in values:
                values.remove(package)
                updated = True
        if updated:
            empty_sections = [k for k, v in optional_dependencies.items() if not v]
            for section in empty_sections:
                del optional_dependencies[section]
    if updated:
        write_pyproject(pyproject)
        msg = f"Removed {package} from {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def _move_ruff_lint_config() -> None:
    """Migrate linting configuration to :code:`tool.ruff.lint`.

    See `this blog <https://astral.sh/blog/ruff-v0.2.0>`_ for details.
    """
    lint_option_keys = {
        "extend-select",
        "ignore",
        "task-tags",
        "isort",
        "pydocstyle",
        "per-file-ignores",
    }
    pyproject = load_pyproject()
    global_settings = get_sub_table(pyproject, "tool.ruff", create=True)
    lint_settings = {k: v for k, v in global_settings.items() if k in lint_option_keys}
    lint_arrays = {k: v for k, v in lint_settings.items() if isinstance(v, Array)}
    if lint_arrays:
        lint_config = get_sub_table(pyproject, "tool.ruff.lint", create=True)
        lint_config.update(lint_arrays)
    lint_tables = {k: v for k, v in lint_settings.items() if isinstance(v, Table)}
    for table in lint_tables:
        lint_config = get_sub_table(pyproject, f"tool.ruff.lint.{table}", create=True)
        lint_config.update(lint_tables[table])
    for key in lint_settings:
        del global_settings[key]
    if lint_arrays or lint_tables:
        write_pyproject(pyproject)
        msg = (
            "Moved linting configuration to [tool.ruff.lint] in"
            f" {CONFIG_PATH.pyproject}"
        )
        raise PrecommitError(msg)


def _update_ruff_config(has_notebooks: bool) -> None:
    executor = Executor()
    executor(__update_global_settings, has_notebooks)
    executor(__update_ruff_format_settings)
    executor(__update_ruff_lint_settings)
    executor(__update_per_file_ignores, has_notebooks)
    executor(__update_isort_settings)
    executor(__update_pydocstyle_settings)
    executor(__remove_nbqa)
    executor.finalize()


def __update_global_settings(has_notebooks: bool) -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff", create=True)
    minimal_settings = {
        "preview": True,
        "show-fixes": True,
        "target-version": ___get_target_version(),
    }
    if has_notebooks:
        key = "extend-include"
        default_includes = ["*.ipynb"]
        minimal_settings[key] = ___merge(default_includes, settings.get(key, []))
    src_directories = ___get_src_directories()
    if src_directories:
        minimal_settings["src"] = src_directories
    typings_dir = "typings"
    if os.path.exists(typings_dir) and os.path.isdir(typings_dir):
        key = "extend-exclude"
        default_excludes = ["typings"]
        minimal_settings[key] = ___merge(default_excludes, settings.get(key, []))
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def ___get_target_version() -> str:
    """Get minimal :code:`target-version` for Ruff.

    >>> ___get_target_version()
    'py37'
    """
    versions = {f'py{v.replace(".", "")}' for v in get_supported_python_versions()}
    versions &= {"py37", "py38", "py39", "py310", "py311", "py312"}
    lowest_version, *_ = sorted(versions, key=natural_sorting)
    return lowest_version


def ___merge(*listings: Iterable[str], enforce_multiline: bool = False) -> Array:
    merged = set()
    for lst in listings:
        merged |= set(lst)
    return to_toml_array(sorted(merged), enforce_multiline)


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


def __update_ruff_format_settings() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.format", create=True)
    minimal_settings = {
        "docstring-code-format": True,
        "line-ending": "lf",
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff formatter configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def __update_ruff_lint_settings() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.lint", create=True)
    ignored_rules = [
        "D101",  # class docstring
        "D102",  # method docstring
        "D103",  # function docstring
        "D105",  # magic method docstring
        "D107",  # init docstring
        "D203",  # conflicts with D211
        "D213",  # multi-line docstring should start at the second line
        "D407",  # missing dashed underline after section
        "D416",  # section name does not have to end with a colon
        "E501",  # line-width already handled by black
        "ISC001",  # conflicts with ruff formatter
        "PLW1514",  # allow missing encoding in open()
        "SIM108",  # allow if-else blocks
    ]
    if "3.6" in get_supported_python_versions():
        ignored_rules.append("UP036")
    ignored_rules = sorted({*settings.get("ignore", []), *ignored_rules})
    minimal_settings = {
        "extend-select": ___get_selected_ruff_rules(),
        "ignore": to_toml_array(ignored_rules),
        "task-tags": ___get_task_tags(settings),
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff linting configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def ___get_selected_ruff_rules() -> Array:
    rules = {
        "A",
        "B",
        "BLE",
        "C4",
        "C90",
        "D",
        "EM",
        "ERA",
        "I",
        "ICN",
        "INP",
        "ISC",
        "N",
        "NPY",
        "PGH",
        "PIE",
        "PL",
        "Q",
        "RET",
        "RSE",
        "RUF",
        "S",
        "SIM",
        "T20",
        "TCH",
        "TID",
        "TRY",
        "UP",
        "YTT",
    }
    python_versions = set(get_supported_python_versions())
    if not {"3.6"} & python_versions:
        rules.add("FA")
    return to_toml_array(sorted(rules))


def ___get_task_tags(ruff_settings: Table) -> Array:
    existing: set[str] = set(ruff_settings.get("task-tags", set()))
    expected = {
        "cspell",
    }
    return to_toml_array(sorted(existing | expected))


def __update_per_file_ignores(has_notebooks: bool) -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.lint.per-file-ignores", create=True)
    minimal_settings = {}
    if has_notebooks:
        key = "*.ipynb"
        default_ignores = {
            "B018",  # useless-expression
            "C90",  # complex-structure
            "D",  # pydocstyle
            "E402",  # import not at top of file
            "E703",  #  useless-semicolon
            "N806",  # non-lowercase-variable-in-function
            "N816",  # mixed-case-variable-in-global-scope
            "PLR09",  # complicated logic
            "PLR2004",  # magic-value-comparison
            "PLW0602",  # global-variable-not-assigned
            "PLW0603",  # global-statement
            "S101",  # `assert` detected
            "T20",  # print found
            "TCH00",  # type-checking block
        }
        expected_rules = ___merge_rules(
            default_ignores,
            ___get_existing_nbqa_ignores(pyproject),
            settings.get(key, []),
        )
        banned_rules = {
            "F821",  # identify variables that are not defined
            "ISC003",  # explicit-string-concatenation
        }
        minimal_settings[key] = ___ban(expected_rules, banned_rules)
    docs_dir = "docs"
    if os.path.exists(docs_dir) and os.path.isdir(docs_dir):
        key = f"{docs_dir}/*"
        default_ignores = {
            "E402",  # import not at top of file
            "INP001",  # implicit namespace package
            "S101",  # `assert` detected
            "S113",  # requests call without timeout
        }
        minimal_settings[key] = ___merge_rules(default_ignores, settings.get(key, []))
    conf_path = f"{docs_dir}/conf.py"
    if os.path.exists(conf_path):
        key = f"{conf_path}"
        default_ignores = {
            "D100",  # no module docstring
        }
        minimal_settings[key] = ___merge_rules(default_ignores, settings.get(key, []))
    if os.path.exists("setup.py"):
        minimal_settings["setup.py"] = to_toml_array(["D100"])
    tests_dir = "tests"
    if os.path.exists(tests_dir) and os.path.isdir(tests_dir):
        key = f"{tests_dir}/*"
        default_ignores = {
            "D",  # no need for pydocstyle
            "INP001",  # allow implicit-namespace-package
            "PGH001",  # allow eval
            "PLC2701",  # private module imports
            "PLR2004",  # magic-value-comparison
            "PLR6301",  # allow non-static method
            "S101",  # allow assert
            "T20",  # allow print and pprint
        }
        minimal_settings[key] = ___merge_rules(default_ignores, settings.get(key, []))
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def ___merge_rules(*rule_sets: Iterable[str], enforce_multiline: bool = False) -> Array:
    """Extend Ruff rules with new rules and filter out redundant ones.

    >>> ___merge_rules(["C90", "B018"], ["D10", "C"])
    ['B018', 'C', 'D10']
    """
    merged = ___merge(*rule_sets)
    filtered = {
        rule
        for rule in merged
        if not any(rule != r and rule.startswith(r) for r in merged)
    }
    return to_toml_array(sorted(filtered), enforce_multiline)


def ___get_existing_nbqa_ignores(pyproject: TOMLDocument) -> set[str]:
    nbqa_table = get_sub_table(pyproject, "tool.nbqa.addopts", create=True)
    if not nbqa_table:
        return set()
    ruff_rules: list[str] = nbqa_table.get("ruff", [])
    return {
        r.replace("--extend-ignore=", "")
        for r in ruff_rules
        if r.startswith("--extend-ignore=")
    }


def ___ban(
    rules: Iterable[str], banned_rules: Iterable[str], enforce_multiline: bool = False
) -> Array:
    """Extend Ruff rules with new rules and filter out redundant ones.

    >>> ___ban(["C90", "B018"], banned_rules=["D10", "C"])
    ['B018']
    """
    banned_set = tuple(banned_rules)
    filtered = {
        rule for rule in rules if not any(rule.startswith(r) for r in banned_set)
    }
    return to_toml_array(sorted(filtered), enforce_multiline)


def __update_isort_settings() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.lint.isort", create=True)
    minimal_settings = {"split-on-trailing-comma": False}
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff isort settings in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def __update_pydocstyle_settings() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.lint.pydocstyle", create=True)
    minimal_settings = {
        "convention": "google",
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def __remove_nbqa() -> None:
    executor = Executor()
    executor(___remove_nbqa_settings)
    executor(remove_precommit_hook, "nbqa-ruff")
    executor.finalize()


def ___remove_nbqa_settings() -> None:
    # cspell:ignore addopts
    pyproject = load_pyproject()
    nbqa_addopts = get_sub_table(pyproject, "tool.nbqa.addopts", create=True)
    if "ruff" in nbqa_addopts:
        del nbqa_addopts["ruff"]
    if not nbqa_addopts:
        tool_table = get_sub_table(pyproject, "tool", create=True)
        del tool_table["nbqa"]
    write_pyproject(pyproject)
    if nbqa_addopts:
        msg = f"Removed Ruff configuration for nbQA from {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def _update_precommit_hook(has_notebooks: bool) -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    yaml = YAML(typ="rt")
    lint_hook = Hook(id="ruff", args=yaml.load("[--fix]"))
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
    update_single_hook_precommit_repo(expected_repo)


def _update_lint_dependencies() -> None:
    if not has_pyproject_build_system():
        return
    pyproject = load_pyproject()
    project_info = get_project_info(pyproject)
    package = project_info.name
    if package is None:
        msg = (
            "Please specify a [project.name] for the package in"
            f" [{CONFIG_PATH.pyproject}]"
        )
        raise PrecommitError(msg)
    python_versions = project_info.supported_python_versions
    if python_versions is not None and "3.6" in python_versions:
        ruff = 'ruff; python_version >="3.7.0"'
    else:
        ruff = "ruff"
    add_dependency(ruff, optional_key=["sty", "dev"])


def _update_vscode_settings() -> None:
    # cspell:ignore charliermarsh
    executor = Executor()
    executor(vscode.add_extension_recommendation, "charliermarsh.ruff")
    executor(
        vscode.update_settings,
        {
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
    executor.finalize()
