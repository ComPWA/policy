"""Check `Ruff <https://ruff.rs>`_ configuration."""

import os
from copy import deepcopy
from textwrap import dedent
from typing import List, Set

from ruamel.yaml.comments import CommentedMap
from tomlkit.items import Array, Table

from repoma.check_dev_files.setup_cfg import (
    has_pyproject_build_system,
    has_setup_cfg_build_system,
)
from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, natural_sorting
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    update_precommit_hook,
    update_single_hook_precommit_repo,
)
from repoma.utilities.project_info import (
    get_project_info,
    get_supported_python_versions,
    open_setup_cfg,
)
from repoma.utilities.pyproject import (
    complies_with_subset,
    get_sub_table,
    load_pyproject,
    to_toml_array,
    update_nbqa_settings,
    write_pyproject,
)
from repoma.utilities.readme import add_badge
from repoma.utilities.vscode import add_extension_recommendation, set_setting


def main() -> None:
    executor = Executor()
    executor(
        add_badge,
        "[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)",
    )
    executor(_check_setup_cfg)
    executor(_update_nbqa_settings)
    executor(_update_ruff_settings)
    executor(_update_ruff_per_file_ignores)
    executor(_update_ruff_pydocstyle_settings)
    executor(_update_precommit_hook)
    executor(_update_precommit_nbqa_hook)
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
    project = get_sub_table(pyproject, "project", create=True)
    old_dependencies = project.get("optional-dependencies")
    new_dependencies = deepcopy(old_dependencies)
    python_versions = project_info.supported_python_versions
    if python_versions is not None and "3.6" in python_versions:
        ruff = 'ruff; python_version >="3.7.0"'
    else:
        ruff = "ruff"
    if new_dependencies is None:
        new_dependencies = dict(
            dev=[f"{package}[sty]"],
            lint=[ruff],
            sty=[f"{package}[lint]"],
        )
    else:
        __add_package(new_dependencies, "dev", f"{package}[sty]")
        __add_package(new_dependencies, "lint", ruff)
        __add_package(new_dependencies, "sty", f"{package}[lint]")
    if old_dependencies != new_dependencies:
        project["optional-dependencies"] = new_dependencies
        write_pyproject(pyproject)
        msg = f"Updated [project.optional-dependencies] in {CONFIG_PATH.pyproject}"
        raise PrecommitError(msg)


def __add_package(optional_dependencies: Table, key: str, package: str) -> None:
    section = optional_dependencies.get(key)
    if section is None:
        optional_dependencies[key] = [package]
    elif package not in section:
        optional_dependencies[key] = to_toml_array(
            sorted({package, *section}, key=lambda s: ('"' in s, s))  # Taplo sorting
        )


def _update_nbqa_settings() -> None:
    # cspell:ignore addopts
    ruff_rules = [
        "--extend-ignore=B018",
        "--extend-ignore=C90",
        "--extend-ignore=D",
        "--extend-ignore=N806",
        "--extend-ignore=N816",
        "--extend-ignore=PLR09",
        "--extend-ignore=PLR2004",
        "--extend-ignore=PLW0602",
        "--extend-ignore=PLW0603",
        "--line-length=85",
    ]
    pyproject = load_pyproject()
    nbqa_table = get_sub_table(pyproject, "tool.nbqa.addopts", create=True)
    ruff_rules.extend(nbqa_table.get("ruff", []))
    ruff_rules = sorted(set(ruff_rules))
    update_nbqa_settings("ruff", to_toml_array(ruff_rules))


def _update_ruff_settings() -> None:
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


def _update_ruff_per_file_ignores() -> None:
    pyproject = load_pyproject()
    settings = get_sub_table(pyproject, "tool.ruff.per-file-ignores", create=True)
    minimal_settings = {}
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


def _update_precommit_hook() -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    expected_hook = CommentedMap(
        repo="https://github.com/astral-sh/ruff-pre-commit",
        hooks=[CommentedMap(id="ruff", args=["--fix"])],
    )
    update_single_hook_precommit_repo(expected_hook)


def _update_precommit_nbqa_hook() -> None:
    if not CONFIG_PATH.precommit.exists():
        return
    update_precommit_hook(
        repo_url="https://github.com/nbQA-dev/nbQA",
        expected_hook=CommentedMap(
            id="nbqa-ruff",
            args=["--fix"],
        ),
    )


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
