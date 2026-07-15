from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from compwa_policy.env.pixi._helpers import has_pixi_config
from compwa_policy.repo.upgrade import (
    get_julia_manifest_paths,
    get_julia_upgrade_command,
    get_uv_upgrade_script,
    has_nested_uv_lock,
)
from compwa_policy.utilities import CONFIG_PATH, append_safe, vscode
from compwa_policy.utilities.match import is_committed
from compwa_policy.utilities.pyproject import (
    ModifiablePyproject,
    Pyproject,
    complies_with_subset,
)
from compwa_policy.utilities.pyproject.setters import split_dependency_definition
from compwa_policy.utilities.readme import add_badge
from compwa_policy.utilities.toml import (
    to_inline_table,
    to_multiline_string,
    to_toml_array,
)

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from tomlkit.items import Table

    from compwa_policy.config import PackageManagerChoice
    from compwa_policy.utilities.pyproject.getters import PythonVersion
    from compwa_policy.utilities.session import Session


def update_pixi_configuration(
    session: Session,
    /,
    is_python_package: bool,
    dev_python_version: PythonVersion,
    package_manager: PackageManagerChoice,
) -> None:
    if "pixi" not in package_manager:
        return
    config = __get_pixi_config(session, package_manager)
    if config is None:
        return
    add_badge(
        session,
        "[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)",
    )
    _rename_workspace_table(config)
    _define_minimal_project(session, package_manager)
    _import_conda_dependencies(config)
    _import_conda_environment(config)
    if package_manager == "pixi+uv":
        _define_combined_ci_job(config)
    else:
        if is_python_package:
            _install_package_editable(config)
        _set_dev_python_version(config, dev_python_version)
        _update_dev_environment(config)
        _update_docnb_and_doclive(config, "tasks")
        _update_docnb_and_doclive(config, "feature.dev.tasks")
    _clean_up_task_env(config)
    _set_upgrade_task(config, package_manager)
    vscode.update_settings(
        session,
        {"files.associations": {"**/pixi.lock": "yaml"}},
    )
    if has_pixi_config(session):
        __update_gitattributes(session)
        __update_gitignore(session)


def __get_pixi_config(
    session: Session,
    package_manager: PackageManagerChoice,
) -> ModifiablePyproject | None:
    if package_manager == "pixi":
        return session.pyproject
    return session.pixi


def _define_combined_ci_job(config: ModifiablePyproject) -> None:
    if not __has_table(config, "feature.dev.tasks"):
        return
    tasks = set(__get_table(config, "feature.dev.tasks"))
    expected = {"linkcheck", "sty"} & tasks
    if {"cov", "coverage"} & tasks:
        expected.add("cov")
    elif "tests" in tasks:
        expected.add("tests")
    if "docnb" in tasks:  # cspelL:ignore docnb
        expected.add("docnb")
    elif "doc" in tasks:
        expected.add("doc")
    ci = __get_table(config, "feature.dev.tasks.ci", create=True)
    existing = set(ci.get("depends_on", set()))
    if not expected <= existing:
        depends_on = expected | existing & tasks
        ci["depends_on"] = to_toml_array(sorted(depends_on))
        msg = "Updated combined CI job for Pixi"
        config.changelog.append(msg)


def _rename_workspace_table(config: ModifiablePyproject) -> None:
    if not __has_table(config, "project"):
        return
    project = __get_table(config, "project")
    workspace = __get_table(config, "workspace", create=True)
    workspace.update(project)
    if config._source == CONFIG_PATH.pyproject:  # noqa: SLF001
        del config._document["tool"]["pixi"]["project"]  # noqa: SLF001
    else:
        del config._document["project"]  # noqa: SLF001  # ty:ignore[invalid-argument-type]
    msg = 'Renamed "project" table to "workspace" in Pixi configuration'
    config.changelog.append(msg)


def _define_minimal_project(
    session: Session,
    package_manager: PackageManagerChoice,
    /,
) -> None:
    """Create a minimal Pixi project definition if it does not exist."""
    config = __get_pixi_config(session, package_manager)
    if config is None:
        return
    table_name = "workspace"
    settings = __get_table(config, table_name, create=True)
    minimal_settings: dict[str, Any] = dict(
        channels=["conda-forge"],
        platforms=["linux-64"],
    )
    if config._source == CONFIG_PATH.pixi_toml:  # noqa: SLF001
        pyproject = session.pyproject
        if pyproject is not None:
            minimal_settings["name"] = pyproject.get_package_name()
    if not complies_with_subset(settings, minimal_settings, exact_value_match=False):
        settings.update(minimal_settings)
        msg = "Defined minimal Pixi project settings"
        config.changelog.append(msg)


def _import_conda_dependencies(config: ModifiablePyproject) -> None:
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
        package, version = __to_pixi_dependency(dep)
        if package in blacklisted_dependencies:
            continue
        expected_dependencies[package] = version
    dependencies = __get_table(config, "dependencies", create=True)
    if not complies_with_subset(dependencies, expected_dependencies):
        dependencies.update(expected_dependencies)
        msg = "Imported conda dependencies into Pixi"
        config.changelog.append(msg)


def __to_pixi_dependency(conda_dependency: str) -> tuple[str, str]:
    """Extract package name and version from a conda dependency string.

    >>> __to_pixi_dependency("julia")
    ('julia', '*')
    >>> __to_pixi_dependency("python==3.9.*")
    ('python', '3.9.*')
    >>> __to_pixi_dependency("graphviz  # for binder")
    ('graphviz', '*')
    >>> __to_pixi_dependency("pip > 19  # needed")
    ('pip', '>19')
    >>> __to_pixi_dependency("compwa-policy!= 3.14")
    ('compwa-policy', '!=3.14')
    >>> __to_pixi_dependency("my_package~=1.2")
    ('my_package', '~=1.2')
    """
    package, operator, version = split_dependency_definition(conda_dependency)
    if not version:
        version = "*"
    if operator in {"=", "=="}:
        operator = ""
    return package, f"{operator}{version}"


def _import_conda_environment(config: ModifiablePyproject) -> None:
    if not CONFIG_PATH.conda.exists():
        return
    with CONFIG_PATH.conda.open() as stream:
        conda = yaml.safe_load(stream)
    conda_variables = {k: str(v) for k, v in conda.get("variables", {}).items()}
    if not conda_variables:
        return
    env_table = __get_table(config, "activation.env", create=True)
    if not complies_with_subset(env_table, conda_variables):
        env_table.update(conda_variables)
        msg = "Imported conda environment variables for Pixi"
        config.changelog.append(msg)


def _clean_up_task_env(config: ModifiablePyproject) -> None:
    if not __has_table(config, "feature.dev.tasks"):
        return
    global_env = __load_pixi_environment_variables(config)
    tasks = __get_table(config, "feature.dev.tasks")
    updated_tasks = []
    for task_name, task_table in tasks.items():
        local_env = task_table.get("env", {})
        if not local_env:
            continue
        expected = to_inline_table({
            k: v for k, v in local_env.items() if v != global_env.get(k)
        })
        if local_env != expected:
            if expected:
                task_table["env"] = expected
            else:
                del task_table["env"]
            updated_tasks.append(task_name)
    if updated_tasks:
        msg = f"Removed redundant environment variables from Pixi tasks {', '.join(updated_tasks)}"
        config.changelog.append(msg)


def __load_pixi_environment_variables(config: ModifiablePyproject) -> dict[str, str]:
    if not __has_table(config, "activation"):
        return {}
    activation_table = __get_table(config, "activation", create=True)
    return dict(activation_table.get("env", {}))


def _install_package_editable(config: ModifiablePyproject) -> None:
    editable = to_inline_table({
        "path": ".",
        "editable": True,
    })
    package_name = config.get_package_name(raise_on_missing=True)
    existing = __get_table(config, "pypi-dependencies", create=True)
    if dict(existing.get(package_name, {})) != dict(editable):
        existing[package_name] = editable
        msg = "Installed Python package in editable mode in Pixi"
        config.changelog.append(msg)


def _set_dev_python_version(
    config: ModifiablePyproject, dev_python_version: PythonVersion
) -> None:
    dependencies = __get_table(config, "dependencies", create=True)
    version = f"{dev_python_version}.*"
    if dependencies.get("python") != version:
        dependencies["python"] = version
        msg = f"Set Python version for Pixi developer environment to {version}"
        config.changelog.append(msg)


def _set_upgrade_task(
    config: ModifiablePyproject, package_manager: PackageManagerChoice
) -> None:
    tasks = __get_table(config, "tasks", create=True)
    helper_tasks: dict[str, dict[str, Any]] = {"_upgrade-pixi": {"cmd": "pixi update"}}
    if is_committed(".pre-commit-config.yaml"):
        helper_tasks["_upgrade-precommit"] = {"cmd": "pre-commit autoupdate -j8"}
    if "uv" in package_manager:
        helper_tasks["_upgrade-uv"] = _get_uv_upgrade_task()
    manifest_paths = get_julia_manifest_paths()
    if manifest_paths:
        helper_tasks["_upgrade-julia"] = _get_julia_upgrade_task(manifest_paths)
    helper_names = {
        "_upgrade-pixi",
        "_upgrade-precommit",
        "_upgrade-uv",
        "_upgrade-julia",
    }
    expected = {
        "depends-on": to_toml_array(helper_tasks),
        "description": "Upgrade all lock files",
    }
    existing_helpers = {name: tasks[name] for name in helper_names if name in tasks}
    if tasks.get("upgrade") != expected or existing_helpers != helper_tasks:
        tasks["upgrade"] = expected
        for name in helper_names - helper_tasks.keys():
            tasks.pop(name, None)
        tasks.update(helper_tasks)
        config.changelog.append("Set Pixi upgrade task")


def _get_uv_upgrade_task() -> dict[str, Any]:
    if not has_nested_uv_lock():
        return {"cmd": "uv lock --upgrade"}
    script = get_uv_upgrade_script()
    return {
        "cmd": to_multiline_string(f"""
uv run --no-project python -c '
{script}
'
""")
    }


def _get_julia_upgrade_task(manifest_paths: list[str]) -> dict[str, Any]:
    command: Any = get_julia_upgrade_command(manifest_paths)
    if "\n" in command:
        command = to_multiline_string(command)
    return {"cmd": command}


def __update_gitattributes(session: Session, /) -> None:
    expected_line = "pixi.lock linguist-language=YAML linguist-generated=true"
    if append_safe(session, expected_line, CONFIG_PATH.gitattributes):
        session.changelog += [
            f"Added linguist definition for pixi.lock under {CONFIG_PATH.gitattributes}"
        ]


def __update_gitignore(session: Session, /) -> None:
    ignore_path = ".pixi/"
    if append_safe(session, ignore_path, CONFIG_PATH.gitignore):
        session.changelog.append(f"Added {ignore_path} under {CONFIG_PATH.gitignore}")


def _update_dev_environment(config: ModifiablePyproject) -> None:
    if not __has_table(config, "project.optional-dependencies"):
        return
    optional_dependencies = __get_table(config, "project.optional-dependencies")
    expected = to_inline_table({
        "features": to_toml_array(sorted(optional_dependencies))
    })
    environments = __get_table(config, "environments", create=True)
    if environments.get("default") != expected:
        environments["default"] = expected
        msg = "Updated Pixi developer environment"
        config.changelog.append(msg)


def _update_docnb_and_doclive(config: ModifiablePyproject, table_key: str) -> None:
    if not __has_table(config, table_key):
        return
    tasks = __get_table(config, table_key)
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
        config.changelog.append(msg)


def ___outsource_cmd(task: Table, other_task_name: str) -> bool:
    expected_cmd = f"pixi run {other_task_name}"
    if task.get("cmd") != expected_cmd:
        task["cmd"] = expected_cmd
        return True
    return False


def __get_table(
    config: ModifiablePyproject, key: str, create: bool = False
) -> MutableMapping[str, Any]:
    if config._source == CONFIG_PATH.pyproject:  # noqa: SLF001
        key = f"tool.pixi.{key}"
    return config.get_table(key, create=create)


def __has_table(config: Pyproject, key: str) -> bool:
    if config._source == CONFIG_PATH.pyproject:  # noqa: SLF001
        key = f"tool.pixi.{key}"
    return config.has_table(key)
