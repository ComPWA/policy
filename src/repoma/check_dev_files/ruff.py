"""Check `Ruff <https://ruff.rs>`_ configuration."""

import os
from textwrap import dedent
from typing import List, Set

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from tomlkit.items import Array, Table
from tomlkit.toml_document import TOMLDocument

from repoma.check_dev_files.setup_cfg import (
    has_pyproject_build_system,
    has_setup_cfg_build_system,
)
from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, natural_sorting, remove_configs
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    remove_precommit_hook,
    update_single_hook_precommit_repo,
)
from repoma.utilities.project_info import (
    get_project_info,
    get_supported_python_versions,
    open_setup_cfg,
)
from repoma.utilities.pyproject import (
    add_dependency,
    complies_with_subset,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    write_pyproject,
)
from repoma.utilities.readme import add_badge, remove_badge
from repoma.utilities.vscode import (
    add_extension_recommendation,
    remove_extension_recommendation,
    remove_settings,
    set_setting,
)


def main(has_notebooks: bool) -> None:
    executor = Executor()
    executor(
        add_badge,
        "[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)",
    )
    executor(_check_setup_cfg)
    executor(_remove_flake8)
    executor(_remove_isort)
    executor(_remove_pydocstyle)
    executor(_remove_pylint)
    executor(_update_ruff_settings, has_notebooks)
    executor(_update_ruff_pydocstyle_settings)
    executor(_update_precommit_hook, has_notebooks)
    executor(_update_pyproject)
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
        lint =
            ruff
            ...
        sty =
            ...
            %(lint)s
            ...
        dev =
            ...
            %(sty)s
            ...
    """
    msg = dedent(msg).strip()
    for section in ("dev", "lint", "sty"):
        if cfg.has_option(extras_require, section):
            continue
        raise PrecommitError(msg)
    lint_section = cfg.get(extras_require, "lint")
    if not any("ruff" in line for line in lint_section.split("\n")):
        raise PrecommitError(msg)


def _remove_flake8() -> None:
    executor = Executor()
    executor(remove_configs, [".flake8"])
    executor(__remove_nbqa_option, "flake8")
    executor(__uninstall, "flake8")
    executor(__uninstall, "pep8-naming")
    executor(remove_extension_recommendation, "ms-python.flake8", unwanted=True)
    executor(remove_precommit_hook, "autoflake")  # cspell:ignore autoflake
    executor(remove_precommit_hook, "flake8")
    executor(remove_precommit_hook, "nbqa-flake8")
    executor(remove_settings, ["flake8.importStrategy"])
    executor.finalize()


def _remove_isort() -> None:
    executor = Executor()
    executor(__remove_isort_settings)
    executor(__remove_nbqa_option, "black")
    executor(__remove_nbqa_option, "isort")
    executor(remove_extension_recommendation, "ms-python.isort", unwanted=True)
    executor(remove_precommit_hook, "isort")
    executor(remove_precommit_hook, "nbqa-isort")
    executor(remove_settings, ["isort.check", "isort.importStrategy"])
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


def __remove_isort_settings() -> None:
    pyproject = load_pyproject()
    if pyproject.get("tool", {}).get("isort") is None:
        return
    pyproject["tool"].remove("isort")  # type: ignore[union-attr]
    write_pyproject(pyproject)
    msg = f"Removed [tool.isort] section from {CONFIG_PATH.pyproject}"
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
    executor(__uninstall, "pydocstyle")
    executor(remove_precommit_hook, "pydocstyle")
    executor.finalize()


def _remove_pylint() -> None:
    executor = Executor()
    executor(remove_configs, [".pylintrc"])  # cspell:ignore pylintrc
    executor(__uninstall, "pylint")
    executor(remove_extension_recommendation, "ms-python.pylint", unwanted=True)
    executor(remove_precommit_hook, "pylint")
    executor(remove_precommit_hook, "nbqa-pylint")
    executor(remove_settings, ["pylint.importStrategy"])
    executor.finalize()


def __uninstall(package: str) -> None:
    __uninstall_from_setup_cfg(package)
    __uninstall_from_pyproject_toml(package)


def __uninstall_from_setup_cfg(package: str) -> None:
    if not os.path.exists(CONFIG_PATH.setup_cfg):
        return
    cfg = open_setup_cfg()
    section = "options.extras_require"
    if not cfg.has_section(section):
        return
    for option in cfg[section]:
        if not cfg.has_option(section, option):
            continue
        if package not in cfg.get(section, option):
            continue
        msg = f'Please remove {package} from the "{section}" section of setup.cfg'
        raise PrecommitError(msg)


def __uninstall_from_pyproject_toml(package: str) -> None:
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
        for values in optional_dependencies.values():
            if package in values:
                values.remove(package)
                updated = True
    if updated:
        write_pyproject(pyproject)
        msg = f"Removed {package} from {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def _update_pyproject() -> None:
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
    executor = Executor()
    executor(add_dependency, ruff, key="lint")
    executor(add_dependency, f"{package}[lint]", key="sty")
    executor(add_dependency, f"{package}[sty]", key="dev")
    executor.finalize()


def _remove_nbqa() -> None:
    executor = Executor()
    executor(__remove_nbqa_settings)
    executor(remove_precommit_hook, "nbqa-ruff")
    executor.finalize()


def __remove_nbqa_settings() -> None:
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


def _update_ruff_settings(has_notebooks: bool) -> None:
    executor = Executor()
    executor(__update_ruff_settings, has_notebooks)
    executor(_update_ruff_per_file_ignores, has_notebooks)
    executor(_remove_nbqa)
    executor.finalize()


def __update_ruff_settings(has_notebooks: bool) -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff", create=True)
    extend_ignore = [
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
        "SIM108",  # allow if-else blocks
    ]
    if "3.6" in get_supported_python_versions():
        extend_ignore.append("UP036")
    ignores = sorted({*settings.get("ignore", []), *extend_ignore})
    minimal_settings = {
        "extend-select": __get_selected_ruff_rules(),
        "ignore": to_toml_array(ignores),
        "show-fixes": True,
        "target-version": __get_target_version(),
        "task-tags": __get_task_tags(settings),
    }
    if has_notebooks:
        extend_include = ["*.ipynb"]
        extend_include = sorted({*settings.get("extend-include", []), *extend_include})
        minimal_settings["extend-include"] = to_toml_array(extend_include)
    src_directories = __get_src_directories()
    if src_directories:
        minimal_settings["src"] = src_directories
    typings_dir = "typings"
    if os.path.exists(typings_dir) and os.path.isdir(typings_dir):
        extend_exclude = {
            "typings",
            *settings.get("extend-exclude", []),
        }
        minimal_settings["extend-exclude"] = to_toml_array(sorted(extend_exclude))
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def __get_ipynb_ignores(pyproject: TOMLDocument, per_file_settings: Table) -> Array:
    notebook_ignores = {
        "B018",  # useless-expression
        "C90",  # complex-structure
        "D",  # pydocstyle
        "E703",  #  useless-semicolon
        "N806",  # non-lowercase-variable-in-function
        "N816",  # mixed-case-variable-in-global-scope
        "PLR09",  # complicated logic
        "PLR2004",  # magic-value-comparison
        "PLW0602",  # global-variable-not-assigned
        "PLW0603",  # global-statement
        "TCH00",  # type-checking block
    }
    notebook_ignores.update(__get_existing_nbqa_ignores(pyproject))
    notebook_ignores.update(per_file_settings.get("*.ipynb", []))
    return to_toml_array(sorted(notebook_ignores))


def __get_existing_nbqa_ignores(pyproject: TOMLDocument) -> Set[str]:
    nbqa_table = get_sub_table(pyproject, "tool.nbqa.addopts", create=True)
    if not nbqa_table:
        return set()
    ruff_rules: List[str] = nbqa_table.get("ruff", [])
    return {
        r.replace("--extend-ignore=", "")
        for r in ruff_rules
        if r.startswith("--extend-ignore=")
    }


def __get_selected_ruff_rules() -> Array:
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


def __get_task_tags(ruff_settings: Table) -> Array:
    existing: Set[str] = set(ruff_settings.get("task-tags", set()))
    expected = {
        "cspell",
    }
    return to_toml_array(sorted(existing | expected))


def __get_src_directories() -> List[str]:
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


def __get_target_version() -> str:
    """Get minimal :code:`target-version` for Ruff.

    >>> __get_target_version()
    'py37'
    """
    versions = {f'py{v.replace(".", "")}' for v in get_supported_python_versions()}
    versions &= {"py37", "py38", "py39", "py310", "py311", "py312"}
    lowest_version, *_ = sorted(versions, key=natural_sorting)
    return lowest_version


def _update_ruff_per_file_ignores(has_notebooks: bool) -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.per-file-ignores", create=True)
    minimal_settings = {}
    if has_notebooks:
        minimal_settings["*.ipynb"] = __get_ipynb_ignores(pyproject, settings)
    docs_dir = "docs"
    if os.path.exists(docs_dir) and os.path.isdir(docs_dir):
        key = f"{docs_dir}/*"
        ignore_codes = {
            "E402",  # import not at top of file
            "INP001",  # implicit namespace package
            "S101",  # `assert` detected
            "S113",  # requests call without timeout
            "T201",  # print found
        }
        ignore_codes.update(settings.get(key, []))  # type: ignore[arg-type]
        minimal_settings[key] = to_toml_array(sorted(ignore_codes))
    if os.path.exists("setup.py"):
        minimal_settings["setup.py"] = to_toml_array(["D100"])
    docs_dir = "tests"
    if os.path.exists(docs_dir) and os.path.isdir(docs_dir):
        key = f"{docs_dir}/*"
        ignore_codes = {
            "D",
            "INP001",
            "PGH001",
            "PLR0913",
            "PLR2004",
            "S101",
        }
        ignore_codes.update(settings.get(key, []))  # type: ignore[arg-type]
        minimal_settings[key] = to_toml_array(sorted(ignore_codes))
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def _update_ruff_pydocstyle_settings() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.pydocstyle", create=True)
    minimal_settings = {
        "convention": "google",
    }
    if not complies_with_subset(settings, minimal_settings):
        settings.update(minimal_settings)
        write_pyproject(pyproject)
        msg = f"Updated Ruff configuration in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def _update_precommit_hook(has_notebooks: bool) -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    yaml = YAML(typ="rt")
    ruff_hook = CommentedMap(id="ruff", args=yaml.load("[--fix]"))
    if has_notebooks:
        types = yaml.load("[python, pyi, jupyter]")
        ruff_hook["types_or"] = types
    expected_repo = CommentedMap(
        repo="https://github.com/astral-sh/ruff-pre-commit",
        hooks=[ruff_hook],
    )
    update_single_hook_precommit_repo(expected_repo)


def _update_vscode_settings() -> None:
    # cspell:ignore charliermarsh
    executor = Executor()
    executor(add_extension_recommendation, "charliermarsh.ruff")
    executor(
        set_setting,
        {
            "ruff.enable": True,
            "ruff.organizeImports": True,
        },
    )
    executor.finalize()
