"""Check Tox configuration file."""

from __future__ import annotations

import re
from configparser import ConfigParser
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomlkit

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import CONFIG_PATH, natural_sorting
from compwa_policy.utilities.pyproject import ModifiablePyproject, Pyproject
from compwa_policy.utilities.toml import to_multiline_string, to_toml_array

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from tomlkit.items import Array, String


def main(has_notebooks: bool) -> None:
    if not CONFIG_PATH.pyproject.is_file():
        return
    with ModifiablePyproject.load() as pyproject:
        _merge_tox_ini_into_pyproject(pyproject)
        _convert_to_native_toml(pyproject)
        if pyproject.has_table("tool.tox"):
            _check_expected_sections(pyproject, has_notebooks)
            _set_minimal_tox_version(pyproject)
            _update_python_test_versions(pyproject)
        pyproject.remove_dependency("tox")
        pyproject.remove_dependency("tox-uv")


def _merge_tox_ini_into_pyproject(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.tox.is_file():
        return
    with open(CONFIG_PATH.tox) as file:
        tox_ini = file.read()
    tox_table = pyproject.get_table("tool.tox", create=True)
    tox_table["legacy_tox_ini"] = __ini_to_toml(tox_ini)
    CONFIG_PATH.tox.unlink()
    msg = f"Merged {CONFIG_PATH.tox} into {CONFIG_PATH.pyproject}"
    pyproject.changelog.append(msg)


def __ini_to_toml(ini: str) -> String:
    ini = re.sub(r"(?<!\\)(\\)(?!\n)", r"\\\\", ini)
    if not re.match(r"^  [^ ]", ini):
        ini = ini.replace("  ", "    ")
    ini = f"\n{ini.strip()}\n"
    return to_multiline_string(ini)


def _convert_to_native_toml(pyproject: ModifiablePyproject) -> None:
    ini_config = read_tox_ini_config()
    if ini_config is None:
        return
    toml_config = pyproject.get_table("tool.tox")
    if "legacy_tox_ini" not in toml_config:
        return
    del toml_config["legacy_tox_ini"]
    for section in ini_config.sections():
        toml_dict = __convert_ini_dict(ini_config[section])
        if section.startswith("testenv"):
            if section == "testenv":
                env_name = "env_run_base"
            else:
                env_name = section.replace("testenv:", "env.")
            env = pyproject.get_table(f"tool.tox.{env_name}", create=True)
            env.update(toml_dict)
        else:
            toml_config.update(toml_dict)
    pyproject.changelog.append("Converted legacy Tox configuration to native TOML")


def __convert_ini_dict(ini: Mapping[str, str]) -> dict[str, Any]:
    toml = {}
    for ini_key, ini_value in ini.items():
        key = ___remap_key(ini_key)
        value = ___convert_ini_value(key, ini_value)
        if key == "commands":
            value = ___convert_commands(ini_value, value)
        # cspell:ignore passenv
        if isinstance(value, str):
            if key == "base":
                value = f"tool.tox.env.{value}"
            if "testenv:" in value:
                value = value.replace("testenv:", "tool.tox.env.")
            if key in {"base", "pass_env"}:
                value = [value]
        toml[key] = value
    return toml


def ___remap_key(key: str) -> str:
    # cspell:disable
    # https://tox.wiki/en/stable/config.html#core
    return {
        "alwayscopy": "always_copy",
        "basepython": "base_python",
        "changedir": "change_dir",
        "env_python": "envpython",
        "envbindir": "env_bin_dir",
        "envdir": "env_dir",
        "envlist": "env_list",
        "envlogdir": "env_log_dir",
        "envname": "env_name",
        "envsitepackagesdir": "env_site_packages_dir",
        "envtmpdir": "env_tmp_dir",
        "ignore_basepython_conflict": "ignore_base_python_conflict",
        "minversion": "min_version",
        "passenv": "pass_env",
        "setenv": "set_env",
        "sitepackages": "system_site_packages",
        "skipsdist": "no_package",
        "toxinidir": "tox_root",
        "toxworkdir": "work_dir",
        "usedevelop": "use_develop",
    }.get(key, key)
    # cspell:enable


def ___convert_ini_value(key: str, value: str) -> Any:
    if value.lower() == "false":
        return False
    if value.lower() == "true":
        return True
    if "\n" in value:
        toml_array = tomlkit.array()
        lines = [s.strip().rstrip(",") for s in value.split("\n")]
        lines = [s for s in lines if s]
        if key == "set_env":
            for line in lines:
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                table_item = tomlkit.inline_table()
                table_item[key.strip()] = value.strip()
                toml_array.append(table_item)
            toml_array.multiline(True)
        else:
            for line in lines:
                toml_array.extend(line.split())
            toml_array.multiline(len(toml_array) > 1)
        return toml_array
    return value


def ___convert_commands(ini_value: str, command: Array) -> Array:
    command = to_toml_array(___merge_posargs(command))
    command.indent(4)
    if len(command) <= 2 or ini_value.strip().startswith("pre-commit"):  # noqa: PLR2004
        command.multiline(False)
    else:
        command.multiline(True)
    command_array = tomlkit.array()
    command_array.multiline(True)
    command_array.append(command)
    return command_array


def ___merge_posargs(commands: Sequence[str]) -> list[str]:  # cspell:ignore posargs
    """Merge commands that contain posargs arguments.

    >>> ___merge_posargs(["pytest", "{posargs:src", "tests/unit}", "--durations=0"])
    ['pytest', '{posargs:src tests/unit}', '--durations=0']
    """
    new_commands: list[str] = []
    merge_mode = False
    for command in commands:
        if merge_mode:
            new_commands[-1] += f" {command}"
        else:
            new_commands.append(command)
        if command.startswith("{posargs:"):
            merge_mode = True
        if command.endswith("}"):
            merge_mode = False
    return new_commands


def _set_minimal_tox_version(pyproject: ModifiablePyproject) -> None:
    tox_table = pyproject.get_table("tool.tox")
    existing_requires = tox_table.get("requires", [])
    minimal_version = "4.21.0"
    if any(
        re.match(rf"^tox\s*(?:>|>=)\s*{re.escape(minimal_version)}$", req.strip())
        for req in existing_requires
    ):
        return
    tox_table["requires"] = to_toml_array([f"tox>={minimal_version}"])
    pyproject.changelog.append(f"Set minimal Tox version to {minimal_version}")


def _check_expected_sections(pyproject: Pyproject, has_notebooks: bool) -> None:
    # cspell:ignore doclive docnb docnblive testenv
    tox_table = pyproject.get_table("tool.tox")
    environments = set(tox_table.get("env", set()))
    expected_environments: set[str] = set()
    if Path("docs").exists():
        expected_environments |= {
            "doc",
            "doclive",
        }
        if has_notebooks:
            expected_environments |= {
                "docnb",
                "docnblive",
                "nb",
            }
    missing_environments = expected_environments - environments
    if missing_environments:
        msg = (
            f"Tox configuration is missing job definitions:"
            f" {', '.join(sorted(missing_environments))}"
        )
        raise PrecommitError(msg)


def _update_python_test_versions(pyproject: ModifiablePyproject) -> None:
    tox_table = pyproject.get_table("tool.tox")
    env_list = tox_table.get("env_list")
    if not env_list:
        return
    if not any(env.startswith("3.") for env in env_list):
        return
    python_versions = pyproject.get_supported_python_versions()
    expected = python_versions + sorted(
        (env for env in env_list if not env.startswith("3.")), key=natural_sorting
    )
    if env_list != expected:
        tox_table["env_list"] = to_toml_array(expected)
        pyproject.changelog.append("Updated tool.tox.env_list")
    label_table = pyproject.get_table("tool.tox.labels", create=True)
    if label_table.get("test") != python_versions:
        label_table["test"] = to_toml_array(python_versions)
        pyproject.changelog.append("Updated tool.tox.labels.test")


def read_tox_ini_config() -> ConfigParser | None:
    if CONFIG_PATH.tox.is_file():
        return _load_tox_ini()
    if CONFIG_PATH.pyproject.is_file():
        pyproject = Pyproject.load()
        if not pyproject.has_table("tool.tox"):
            return None
        tox_table = pyproject.get_table("tool.tox")
        tox_config_str = tox_table.get("legacy_tox_ini")
        if tox_config_str is not None:
            config = ConfigParser()
            config.read_string(tox_config_str)
            return config
    return None


def _load_tox_ini() -> ConfigParser:
    config = ConfigParser()
    config.read(CONFIG_PATH.tox)
    return config
