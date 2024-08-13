"""Update pixi implementation."""

from __future__ import annotations

import re
from textwrap import dedent
from typing import TYPE_CHECKING

import yaml
from tomlkit import inline_table, string

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, append_safe, vscode
from compwa_policy.utilities.cfg import open_config
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.match import filter_files
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    complies_with_subset,
)
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from configparser import ConfigParser
    from pathlib import Path

    from tomlkit.items import InlineTable, String, Table

    from compwa_policy.check_dev_files.conda import PackageManagerChoice
    from compwa_policy.utilities.pyproject.getters import PythonVersion


def main(
    package_managers: set[PackageManagerChoice],
    is_python_package: bool,
    dev_python_version: PythonVersion,
    outsource_pixi_to_tox: bool,
) -> None:
    if "pixi" in package_managers:
        _update_pixi_configuration(
            is_python_package, dev_python_version, outsource_pixi_to_tox
        )
    else:
        _remove_pixi_configuration()


def _update_pixi_configuration(
    is_python_package: bool,
    dev_python_version: PythonVersion,
    outsource_pixi_to_tox: bool,
) -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(__configure_setuptools_scm, pyproject)
        do(__define_minimal_project, pyproject)
        if is_python_package:
            do(__install_package_editable, pyproject)
        do(__import_conda_dependencies, pyproject)
        do(__import_conda_environment, pyproject)
        do(__import_tox_tasks, pyproject)
        do(__define_combined_ci_job, pyproject)
        do(__set_dev_python_version, pyproject, dev_python_version)
        do(__update_dev_environment, pyproject)
        do(__clean_up_task_env, pyproject)
        do(__update_docnb_and_doclive, pyproject, "tool.pixi.tasks")
        do(__update_docnb_and_doclive, pyproject, "tool.pixi.feature.dev.tasks")
        do(
            vscode.update_settings,
            {"files.associations": {"**/pixi.lock": "yaml"}},
        )
        if outsource_pixi_to_tox:
            do(__outsource_pixi_tasks_to_tox, pyproject)
        if has_pixi_config(pyproject):
            do(__update_gitattributes)
            do(__update_gitignore)


def __configure_setuptools_scm(pyproject: ModifiablePyproject) -> None:
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


def __define_combined_ci_job(pyproject: ModifiablePyproject) -> None:
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


def __define_minimal_project(pyproject: ModifiablePyproject) -> None:
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


def __import_conda_dependencies(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.conda.exists():
        return
    with CONFIG_PATH.conda.open() as stream:
        conda = yaml.safe_load(stream)
    conda_dependencies = conda.get("dependencies", [])
    if not conda_dependencies:
        return
    blacklisted_dependencies = {"pip"}
    expected_dependencies = {}
    for dep in conda.get("dependencies", []):
        if not isinstance(dep, str):
            continue
        package, version = ___to_pixi_dependency(dep)
        if package in blacklisted_dependencies:
            continue
        expected_dependencies[package] = version
    dependencies = pyproject.get_table("tool.pixi.dependencies", create=True)
    if not complies_with_subset(dependencies, expected_dependencies):
        dependencies.update(expected_dependencies)
        msg = "Imported conda dependencies into Pixi"
        pyproject.append_to_changelog(msg)


def ___to_pixi_dependency(conda_dependency: str) -> tuple[str, str]:
    """Extract package name and version from a conda dependency string.

    >>> ___to_pixi_dependency("julia")
    ('julia', '*')
    >>> ___to_pixi_dependency("python==3.9.*")
    ('python', '3.9.*')
    >>> ___to_pixi_dependency("graphviz  # for binder")
    ('graphviz', '*')
    >>> ___to_pixi_dependency("pip > 19  # needed")
    ('pip', '>19')
    >>> ___to_pixi_dependency("compwa-policy!= 3.14")
    ('compwa-policy', '!=3.14')
    >>> ___to_pixi_dependency("my_package~=1.2")
    ('my_package', '~=1.2')
    """
    matches = re.match(r"^([a-zA-Z0-9_-]+)([\!<=>~\s]*)([^ ^#]*)", conda_dependency)
    if not matches:
        msg = f"Could not extract package name and version from {conda_dependency}"
        raise ValueError(msg)
    package, operator, version = matches.groups()
    if not version:
        version = "*"
    if operator in {"=", "=="}:
        operator = ""
    return package.strip(), f"{operator.strip()}{version.strip()}"


def __import_conda_environment(pyproject: ModifiablePyproject) -> None:
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
        new_env = pixi_variables
        new_env.update(conda_variables)
        activation_table["env"] = new_env
        msg = "Imported conda environment variables for Pixi"
        pyproject.append_to_changelog(msg)


def __import_tox_tasks(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.tox.exists():
        return
    tox = open_config(CONFIG_PATH.tox)
    tox_jobs = ___get_tox_job_names(tox)
    imported_tasks = []
    blacklisted_jobs = {"jcache"}  # cspell:ignore jcache
    for job_name, task_name in tox_jobs.items():
        if job_name in blacklisted_jobs:
            continue
        pixi_table_name = f"tool.pixi.feature.dev.tasks.{task_name}"
        if pyproject.has_table(pixi_table_name):
            continue
        section = f"testenv:{job_name}" if job_name else "testenv"
        if not tox.has_option(section, "commands"):
            continue
        command = tox.get(section, option="commands", raw=True)
        pixi_table = pyproject.get_table(pixi_table_name, create=True)
        pixi_table["cmd"] = ___to_pixi_command(command)
        if tox.has_option(section, "setenv"):  # cspell:ignore setenv
            job_environment = tox.get(section, option="setenv", raw=True)
            environment_variables = ___convert_tox_environment_variables(
                job_environment
            )
            if environment_variables:
                pixi_table["env"] = environment_variables
        imported_tasks.append(task_name)
    if imported_tasks:
        msg = f"Imported the following tox jobs: {', '.join(sorted(imported_tasks))}"
        pyproject.append_to_changelog(msg)


def ___get_tox_job_names(cfg: ConfigParser) -> dict[str, str]:
    tox_jobs = [
        section[8:]
        for section in cfg.sections()
        if section.startswith("testenv")  # cspell:ignore testenv
    ]
    return {job: job or "tests" for job in tox_jobs}


def ___convert_tox_environment_variables(tox_env: str) -> InlineTable:
    lines = tox_env.splitlines()
    lines = [s.strip() for s in lines]
    lines = [s for s in lines if s]
    environment_variables = inline_table()
    for line in lines:
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        environment_variables[key] = string(value.strip())
    return environment_variables


def __clean_up_task_env(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("tool.pixi.feature.dev.tasks"):
        return
    global_env = ___load_pixi_environment_variables(pyproject)
    tasks = pyproject.get_table("tool.pixi.feature.dev.tasks")
    updated_tasks = []
    for task_name, task_table in tasks.items():
        local_env = task_table.get("env", {})
        if not local_env:
            continue
        expected = inline_table()
        expected.update({k: v for k, v in local_env.items() if v != global_env.get(k)})
        if local_env != expected:
            if expected:
                task_table["env"] = expected
            else:
                del task_table["env"]
            updated_tasks.append(task_name)
    if updated_tasks:
        msg = f"Removed redundant environment variables from Pixi tasks {', '.join(updated_tasks)}"
        pyproject.append_to_changelog(msg)


def ___load_pixi_environment_variables(pyproject: Pyproject) -> dict[str, str]:
    if not pyproject.has_table("tool.pixi.activation"):
        return {}
    activation_table = pyproject.get_table("tool.pixi.activation", create=True)
    return dict(activation_table.get("env", {}))


def ___to_pixi_command(tox_command: str) -> String:
    """Convert a tox command to a Pixi command.

    >>> ___to_pixi_command("pytest {posargs}")
    'pytest'
    >>> ___to_pixi_command("pytest {posargs:benchmarks}")
    'pytest benchmarks'
    >>> ___to_pixi_command("pytest {posargs src tests}")
    'pytest src tests'
    """
    # cspell:ignore posargs
    tox_command = re.sub(r"\s*{posargs:?\s*([^}]*)}", r" \1", tox_command)
    pixi_command = dedent(tox_command).strip()
    if "\n" in pixi_command:
        pixi_command = "\n" + pixi_command + "\n"
        pixi_command = pixi_command.replace("\\\n", "\\\n" + 4 * " ")
    return string(pixi_command, multiline="\n" in pixi_command)


def __install_package_editable(pyproject: ModifiablePyproject) -> None:
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


def __outsource_pixi_tasks_to_tox(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.tox.exists():
        return
    tox = open_config(CONFIG_PATH.tox)
    blacklisted_jobs = {"sty"}
    updated_tasks = []
    for tox_job, pixi_task in ___get_tox_job_names(tox).items():
        if pixi_task in blacklisted_jobs:
            continue
        if not pyproject.has_table(f"tool.pixi.feature.dev.tasks.{pixi_task}"):
            continue
        task = pyproject.get_table(f"tool.pixi.feature.dev.tasks.{pixi_task}")
        expected_cmd = f"tox -e {tox_job}"
        if task.get("cmd") != expected_cmd:
            task["cmd"] = expected_cmd
            task.pop("env", None)
            updated_tasks.append(pixi_task)
    if updated_tasks:
        msg = f"Outsourced Pixi tasks to tox: {', '.join(updated_tasks)}"
        pyproject.append_to_changelog(msg)


def __set_dev_python_version(
    pyproject: ModifiablePyproject, dev_python_version: PythonVersion
) -> None:
    dependencies = pyproject.get_table("tool.pixi.dependencies", create=True)
    version = f"{dev_python_version}.*"
    if dependencies.get("python") != version:
        dependencies["python"] = version
        msg = f"Set Python version for Pixi developer environment to {version}"
        pyproject.append_to_changelog(msg)


def __update_gitattributes() -> None:
    expected_line = "pixi.lock linguist-language=YAML linguist-generated=true"
    if append_safe(expected_line, CONFIG_PATH.gitattributes):
        msg = (
            f"Added linguist definition for pixi.lock under {CONFIG_PATH.gitattributes}"
        )
        raise PrecommitError(msg)


def __update_gitignore() -> None:
    ignore_path = ".pixi/"
    if append_safe(ignore_path, CONFIG_PATH.gitignore):
        msg = f"Added {ignore_path} under {CONFIG_PATH.gitignore}"
        raise PrecommitError(msg)


def __update_dev_environment(pyproject: ModifiablePyproject) -> None:
    if not pyproject.has_table("project.optional-dependencies"):
        return
    optional_dependencies = pyproject.get_table("project.optional-dependencies")
    expected = inline_table()
    expected["features"] = to_toml_array(sorted(optional_dependencies))
    environments = pyproject.get_table("tool.pixi.environments", create=True)
    if environments.get("default") != expected:
        environments["default"] = expected
        msg = "Updated Pixi developer environment"
        pyproject.append_to_changelog(msg)


def __update_docnb_and_doclive(pyproject: ModifiablePyproject, table_key: str) -> None:
    if not pyproject.has_table(table_key):
        return
    tasks = pyproject.get_table(table_key)
    tables_to_overwrite = {
        "doc": ["docnb", "docnb-force"],
        "doclive": ["docnblive"],
    }
    updated_tasks = []
    for template_task_name, target_task_names in tables_to_overwrite.items():
        for task_name in target_task_names:
            task = tasks.get(task_name)
            if task is None:
                continue
            if ___outsource_cmd(task, template_task_name):
                updated_tasks.append(task_name)
    if updated_tasks:
        msg = f"Updated `cmd` of Pixi tasks {', '.join(updated_tasks)}"
        pyproject.append_to_changelog(msg)


def ___outsource_cmd(task: Table, other_task_name: str) -> bool:
    expected_cmd = f"pixi run {other_task_name}"
    if task.get("cmd") != expected_cmd:
        task["cmd"] = expected_cmd
        return True
    return False


def _remove_pixi_configuration() -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(__remove_pixi_configuration, pyproject)


def __remove_pixi_configuration(pyproject: ModifiablePyproject) -> None:
    updated = False
    updated |= ___remove(CONFIG_PATH.pixi_lock)
    updated |= ___remove(CONFIG_PATH.pixi_toml)
    if pyproject.has_table("tool.pixi"):
        del pyproject._document["tool"]["pixi"]  # pyright: ignore[reportTypedDictNotRequiredAccess] # noqa: SLF001
        updated = True
    if updated:
        msg = "Removed Pixi configuration files"
        pyproject.append_to_changelog(msg)


def ___remove(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink(missing_ok=True)
    return True


def has_pixi_config(pyproject: Pyproject | None = None) -> bool:
    if filter_files(["pixi.lock", "pixi.toml"]):
        return True
    if pyproject is not None:
        return pyproject.has_table("tool.pixi")
    return CONFIG_PATH.pyproject.exists() and Pyproject.load().has_table("tool.pixi")
