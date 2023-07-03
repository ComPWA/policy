"""Check `Ruff <https://ruff.rs>`_ configuration."""

import os
from textwrap import dedent
from typing import List, Set

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from tomlkit.items import Array, Table

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, natural_sorting
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    update_precommit_hook,
    update_single_hook_precommit_repo,
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
from repoma.utilities.setup_cfg import get_supported_python_versions, open_setup_cfg
from repoma.utilities.vscode import add_extension_recommendation, set_setting


def main() -> None:
    executor = Executor()
    executor(
        add_badge,
        "[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)",
    )
    executor(_check_setup_cfg)
    executor(_update_ruff_settings)
    executor(_update_ruff_per_file_ignores)
    executor(_update_ruff_pydocstyle_settings)
    executor(_update_precommit_hook)
    executor(_update_precommit_nbqa_hook)
    executor(_update_vscode_settings)
    executor(update_nbqa_settings, "ruff", to_toml_array(["--line-length=85"]))
    executor.finalize()


def _check_setup_cfg() -> None:
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
    lint_section = cfg.get(extras_require, "lint").split("\n")
    if "ruff" not in lint_section:
        raise PrecommitError(msg)


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
    ]
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
        rev=DoubleQuotedScalarString(""),
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
