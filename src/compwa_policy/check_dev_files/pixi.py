"""Update pixi implementation."""

from __future__ import annotations

import re
from configparser import ConfigParser
from textwrap import dedent
from typing import TYPE_CHECKING

import yaml
from tomlkit import inline_table, string

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    complies_with_subset,
)
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from tomlkit.items import InlineTable, String, Table

    from compwa_policy.utilities.pyproject.getters import PythonVersion


def main(is_python_package: bool, dev_python_version: PythonVersion) -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_configure_setuptools_scm, pyproject)
        do(_define_minimal_project, pyproject)
        if is_python_package:
            do(_install_package_editable, pyproject)
        do(_import_conda_environment, pyproject)
        do(_import_tox_tasks, pyproject)
        do(_define_combined_ci_job, pyproject)
        do(_set_dev_python_version, pyproject, dev_python_version)
        do(_update_dev_environment, pyproject)
        do(_clean_up_task_env, pyproject)
        do(_update_docnb_and_doclive, pyproject, "tool.pixi.tasks")
        do(_update_docnb_and_doclive, pyproject, "tool.pixi.feature.dev.tasks")
        do(
            vscode.update_settings,
            {"files.associations": {"**/pixi.lock": "yaml"}},
        )


def _configure_setuptools_scm(pyproject: ModifiablePyproject) -> None:
    """Configure :code:`setuptools_scm` to not include git info in package version."""
    if not pyproject.has_table("tool.setuptools_scm"):
        return
    setuptools_scm = pyproject.get_table("tool.setuptools_scm")
    expected_scheme = {
        "local_scheme": "no-local-version",
        "version_scheme": "post-release",
    }
    if not complies_with_subset(setuptools_scm, expected_scheme):
        setuptools_scm.update(expected_scheme)
        msg = "Configured setuptools_scm to not include git info in package version for pixi"
        pyproject.append_to_changelog(msg)


def _define_combined_ci_job(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("tool.pixi.feature.dev.tasks"):
        return
    tasks = set(pyproject.get_table("tool.pixi.feature.dev.tasks"))
    expected = {"linkcheck", "sty"} & tasks
    if {"cov", "coverage"} & tasks:
        expected.add("cov")
    elif "tests" in tasks:
        expected.add("tests")
    if "docnb" in tasks:  # cspelL:ignore docnb
        expected.add("docnb")
    elif "doc" in tasks:
        expected.add("doc")
    ci = pyproject.get_table("tool.pixi.feature.dev.tasks.ci", create=True)
    existing = set(ci.get("depends_on", set()))
    if not expected <= existing:
        depends_on = expected | existing & tasks
        ci["depends_on"] = to_toml_array(sorted(depends_on), multiline=False)
        msg = "Updated combined CI job for Pixi"
        pyproject.append_to_changelog(msg)


def _define_minimal_project(pyproject: ModifiablePyproject) -> None:
    """Create a minimal Pixi project definition if it does not exist."""
    settings = pyproject.get_table("tool.pixi.project", create=True)
    minimal_settings = dict(
        channels=["conda-forge"],
        platforms=["linux-64"],
    )
    if not complies_with_subset(settings, minimal_settings, exact_value_match=False):
        settings.update(minimal_settings)
        msg = "Defined minimal Pixi project settings"
        pyproject.append_to_changelog(msg)


def _import_conda_environment(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.conda.exists():
        return
    with CONFIG_PATH.conda.open() as stream:
        conda = yaml.safe_load(stream)
    conda_variables = {k: str(v) for k, v in conda.get("variables", {}).items()}
    if not conda_variables:
        return
    activation_table = pyproject.get_table("tool.pixi.activation", create=True)
    pixi_variables = dict(activation_table.get("env", {}))
    if not complies_with_subset(pixi_variables, conda_variables):
        activation_table["env"] = dict(**pixi_variables, **conda_variables)
        msg = "Imported conda environment variables for Pixi"
        pyproject.append_to_changelog(msg)


def _import_tox_tasks(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.tox.exists():
        return
    cfg = ConfigParser()
    cfg.read(CONFIG_PATH.tox)
    tox_jobs = [
        section[8:]
        for section in cfg.sections()
        if section.startswith("testenv")  # cspell:ignore testenv
    ]
    imported_tasks = []
    for job_name in tox_jobs:
        task_name = job_name or "tests"
        pixi_table_name = f"tool.pixi.feature.dev.tasks.{task_name}"
        if pyproject.has_table(pixi_table_name):
            continue
        section = f"testenv:{job_name}" if job_name else "testenv"
        if not cfg.has_option(section, "commands"):
            continue
        command = cfg.get(section, option="commands", raw=True)
        pixi_table = pyproject.get_table(pixi_table_name, create=True)
        pixi_table["cmd"] = __to_pixi_command(command)
        if cfg.has_option(section, "setenv"):  # cspell:ignore setenv
            job_environment = cfg.get(section, option="setenv", raw=True)
            environment_variables = __convert_tox_environment_variables(
                job_environment,
                blacklisted_keys={"FORCE_COLOR"},
            )
            if environment_variables:
                pixi_table["env"] = environment_variables
        imported_tasks.append(task_name)
    if imported_tasks:
        msg = f"Imported the following tox jobs: {', '.join(sorted(imported_tasks))}"
        pyproject.append_to_changelog(msg)


def __convert_tox_environment_variables(
    tox_env: str, blacklisted_keys: set[str]
) -> InlineTable:
    lines = tox_env.splitlines()
    lines = [s.strip() for s in lines]
    lines = [s for s in lines if s]
    environment_variables = inline_table()
    for line in lines:
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        if key in blacklisted_keys:
            continue
        environment_variables[key] = string(value.strip())
    return environment_variables


def _clean_up_task_env(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("tool.pixi.feature.dev.tasks"):
        return
    global_env = __load_pixi_environment_variables(pyproject)
    tasks = pyproject.get_table("tool.pixi.feature.dev.tasks")
    updated_tasks = []
    for task_name, task_table in tasks.items():
        local_env = task_table.get("env", {})
        if not local_env:
            continue
        expected = {k: v for k, v in local_env.items() if v != global_env.get(k)}
        if local_env != expected:
            if expected:
                task_table["env"] = expected
            else:
                del task_table["env"]
            updated_tasks.append(task_name)
    if updated_tasks:
        msg = f"Removed redundant environment variables from Pixi tasks {', '.join(updated_tasks)}"
        pyproject.append_to_changelog(msg)


def __load_pixi_environment_variables(pyproject: Pyproject) -> dict[str, str]:
    if not pyproject.has_table("tool.pixi.activation"):
        return {}
    activation_table = pyproject.get_table("tool.pixi.activation", create=True)
    return dict(activation_table.get("env", {}))


def __to_pixi_command(tox_command: str) -> String:
    tox_command = re.sub(r" {posargs[^}]*}", "", tox_command)  # cspell:ignore posargs
    pixi_command = dedent(tox_command).strip()
    if "\n" in pixi_command:
        pixi_command = "\n" + pixi_command + "\n"
        pixi_command = pixi_command.replace("\\\n", "\\\n" + 4 * " ")
    return string(pixi_command, multiline="\n" in pixi_command)


def _install_package_editable(pyproject: ModifiablePyproject) -> None:
    editable = inline_table()
    editable.update({
        "path": ".",
        "editable": True,
    })
    package_name = pyproject.get_package_name(raise_on_missing=True)
    existing = pyproject.get_table("tool.pixi.pypi-dependencies", create=True)
    if dict(existing.get(package_name, {})) != dict(editable):
        existing[package_name] = editable
        msg = "Installed Python package in editable mode in Pixi"
        pyproject.append_to_changelog(msg)


def _set_dev_python_version(
    pyproject: ModifiablePyproject, dev_python_version: PythonVersion
) -> None:
    dependencies = pyproject.get_table("tool.pixi.dependencies", create=True)
    version = f"{dev_python_version}.*"
    if dependencies.get("python") != version:
        dependencies["python"] = version
        msg = f"Set Python version for Pixi developer environment to {version}"
        pyproject.append_to_changelog(msg)


def _update_dev_environment(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("project.optional-dependencies"):
        return
    optional_dependencies = sorted(pyproject.get_table("project.optional-dependencies"))
    expected = inline_table()
    expected.update({
        "features": to_toml_array(optional_dependencies),
        "solve-group": "default",
    })
    environments = pyproject.get_table("tool.pixi.environments", create=True)
    package_name = pyproject.get_package_name(raise_on_missing=True)
    if environments.get(package_name) != expected:
        environments[package_name] = expected
        msg = "Updated Pixi developer environment"
        pyproject.append_to_changelog(msg)


def _update_docnb_and_doclive(pyproject: ModifiablePyproject, table_key: str) -> None:
    if not pyproject.has_table(table_key):
        return
    tasks = pyproject.get_table(table_key)
    tables_to_overwrite = {
        "doc": ["docnb", "docnb-force"],
        "doclive": ["docnblive"],
    }
    updated_tasks = []
    for template_task_name, target_task_names in tables_to_overwrite.items():
        template_task = tasks.get(template_task_name)
        if template_task is None:
            continue
        for task_name in target_task_names:
            task = tasks.get(task_name)
            if task is None:
                continue
            if ___overwrite_cmd(task, template_task):
                updated_tasks.append(task_name)
    if updated_tasks:
        msg = f"Updated `cmd` of Pixi tasks {', '.join(updated_tasks)}"
        pyproject.append_to_changelog(msg)


def ___overwrite_cmd(task: Table, template_task: Table) -> bool:
    template_cmd = template_task.get("cmd")
    if not template_cmd:
        msg = f"Missing cmd for template task {template_task.name}"
        raise ValueError(msg)
    if task.get("cmd") != template_cmd:
        task["cmd"] = template_task["cmd"]
        return True
    return False
