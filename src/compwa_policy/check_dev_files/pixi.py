"""Update pixi implementation."""

from configparser import ConfigParser
from textwrap import dedent

from tomlkit import inline_table, string
from tomlkit.items import String

from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.pyproject import ModifiablePyproject, complies_with_subset
from compwa_policy.utilities.pyproject.getters import PythonVersion
from compwa_policy.utilities.toml import to_toml_array


def main(is_python_package: bool, dev_python_version: PythonVersion) -> None:
    with Executor() as do, ModifiablePyproject.load() as pyproject:
        do(_configure_setuptools_scm, pyproject)
        do(_define_minimal_project, pyproject)
        if is_python_package:
            do(_install_package_editable, pyproject)
        do(_import_tox_tasks, pyproject)
        do(_set_dev_python_version, pyproject, dev_python_version)
        do(_update_dev_environment, pyproject)
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
    imported_jobs = []
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
        imported_jobs.append(job_name)
    if imported_jobs:
        msg = f"Imported the following tox jobs: {', '.join(imported_jobs)}"
        pyproject.append_to_changelog(msg)


def __to_pixi_command(tox_command: str) -> String:
    tox_command = tox_command.replace(" {posargs}", "")  # cspell:ignore posargs
    pixi_command = dedent(tox_command).strip()
    pixi_command = pixi_command.replace(" {posargs}", "")
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
