"""Check and update :code:`pytest` settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import rtoml
from ini2toml.api import Translator

from compwa_policy.errors import PolicyError
from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.cfg import open_config
from compwa_policy.utilities.check_hook import check_hook
from compwa_policy.utilities.pyproject import ModifiablePyproject, has_dependency
from compwa_policy.utilities.toml import to_toml_array

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableMapping

    from tomlkit.items import Array

    from compwa_policy import Arguments
    from compwa_policy.utilities.check_hook import CheckContext
    from compwa_policy.utilities.session import Session


@check_hook(
    group="python",
    paths=[
        CONFIG_PATH.precommit,
        CONFIG_PATH.pyproject,
        CONFIG_PATH.pytest_ini,
        CONFIG_PATH.vscode_settings,
    ],
    enabled=lambda _args, ctx: ctx.is_python_repo,
)
def check(session: Session, args: Arguments, _: CheckContext) -> None:
    config = session.pyproject
    if config is None or not has_dependency(config, "pytest"):
        return
    _merge_coverage_into_pyproject(config)
    _merge_pytest_into_pyproject(config)
    _deny_ini_options(config)
    _update_codecov_settings(config, args.branch_coverage)
    _update_settings(config)
    _update_vscode_settings(
        session, args.allow_vscode_coverage_gutters, args.pytest_single_threaded
    )
    if args.pytest_single_threaded:
        config.remove_dependency("pytest-xdist")
    else:
        config.add_dependency("pytest-xdist", ["test", "dev"])


def _merge_coverage_into_pyproject(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.pytest_ini.exists():
        return
    pytest_ini = open_config(CONFIG_PATH.pytest_ini)
    section_name = "coverage:run"
    if not pytest_ini.has_section(section_name):
        return
    coverage_config: dict = dict(pytest_ini[section_name])
    for key, value in coverage_config.items():
        if value in {"False", "True"}:
            coverage_config[key] = bool(value)
        if key == "source" and isinstance(value, str):
            coverage_config[key] = [value]
    tool_table = pyproject.get_table("tool.coverage.run", create=True)
    tool_table.update(coverage_config)
    msg = f"Imported Coverage.py configuration from {CONFIG_PATH.pytest_ini}"
    pyproject.changelog.append(msg)


def _merge_pytest_into_pyproject(pyproject: ModifiablePyproject) -> None:
    if not CONFIG_PATH.pytest_ini.exists():
        return
    with open(CONFIG_PATH.pytest_ini) as stream:
        original_contents = stream.read()
    toml_str = Translator().translate(original_contents, profile_name="pytest.ini")
    pytest_config = rtoml.loads(toml_str)
    pytest_config.pop("coverage:run", None)
    tool_table = pyproject.get_table("tool", create=True)
    tool_table.update(pytest_config)
    CONFIG_PATH.pytest_ini.unlink()
    msg = f"Imported pytest configuration from {CONFIG_PATH.pytest_ini}"
    pyproject.changelog.append(msg)


def _deny_ini_options(pyproject: ModifiablePyproject) -> None:
    if pyproject.has_table("tool.pytest.ini_options"):
        msg = (
            "pytest.ini_options found in pyproject.toml. Have a look at"
            " https://docs.pytest.org/en/stable/reference/customize.html#pyproject-toml"
            " to migrate to a native TOML configuration."
        )
        raise PolicyError(msg)
    pytest_config = pyproject.get_table("tool.pytest", fallback=None)
    if pytest_config is None:
        return
    if "minversion" in pytest_config:  # cspell:ignore minversion
        return
    pytest_config["minversion"] = "9.0"
    pyproject.changelog.append("Set minimum pytest version to 9.0")


def _update_settings(pyproject: ModifiablePyproject) -> None:
    table_key = "tool.pytest"
    if not pyproject.has_table(table_key):
        return
    config = pyproject.get_table(table_key)
    existing = config.get("addopts", "")
    expected = __get_expected_addopts(existing)
    if isinstance(existing, str) or sorted(existing) != sorted(expected):
        config["addopts"] = expected
        msg = f"Updated [{table_key}]"
        pyproject.changelog.append(msg)


def __get_expected_addopts(existing: str | Iterable) -> Array:
    if isinstance(existing, str):
        options = {opt.strip() for opt in __split_options(existing)}
    else:
        options = set(existing)
    options = {opt for opt in options if opt and not opt.startswith("--color=")}
    options.update(["--color=yes", "--import-mode=importlib"])
    return to_toml_array(sorted(options))


def __split_options(arg: str) -> list[str]:
    """Split a string of options into a list of options.

    >>> __split_options('-abc def -ghi "j k l" -mno pqr')
    ['-abc def', '-ghi "j k l"', '-mno pqr']
    """
    elements = arg.split()
    options: list[str] = []
    for i in range(len(elements)):
        if i > 0 and not elements[i].startswith("-"):
            options[-1] += f" {elements[i]}"
        else:
            options.append(elements[i])
    return options


def _update_codecov_settings(
    pyproject: ModifiablePyproject, branch_coverage: bool = True
) -> None:
    if not has_dependency(pyproject, ("coverage", "pytest-cov")):
        return
    updated = __update_settings(
        config=pyproject.get_table("tool.coverage.run", create=True),
        branch=branch_coverage,
        omit=to_toml_array([
            # https://github.com/microsoft/vscode-python/issues/24973#issuecomment-2886889888
            "benchmarks/**/*.py",
            "docs/**/*.ipynb",
            "docs/**/*.py",
            "examples/**/*.py",
            "tests/**/*.py",
        ]),
        source=["src"],
    )
    updated |= __update_settings(
        config=pyproject.get_table("tool.coverage.report", create=True),
        exclude_also=to_toml_array(["if TYPE_CHECKING:"], multiline=True),
    )
    if updated:
        msg = "Updated pytest coverage settings"
        pyproject.changelog.append(msg)


def __update_settings(config: MutableMapping, **expected: Any) -> bool:
    original_config = dict(config)
    config.update(expected)
    return dict(config) != original_config


def _update_vscode_settings(
    session: Session,
    /,
    coverage_gutters: bool,
    single_threaded: bool,
) -> None:
    # cspell:ignore ryanluker
    if coverage_gutters:
        vscode.add_extension_recommendation(
            session,
            "ryanluker.vscode-coverage-gutters",
        )
    else:
        vscode.remove_extension_recommendation(
            session,
            extension_name="ryanluker.vscode-coverage-gutters",
            unwanted=True,
        )
    vscode.update_settings(
        session,
        {
            "testing.coverageToolbarEnabled": True,
            "testing.showCoverageInExplorer": True,
        },
    )
    vscode.remove_settings(
        session, {"python.testing.pytestArgs": ["--color=no", "--no-cov"]}
    )
    pyproject = session.pyproject
    package_name = pyproject.get_package_name() if pyproject is not None else None
    if package_name is not None:
        module_name = package_name.replace("-", "_")
        vscode.remove_settings(
            session, {"python.testing.pytestArgs": [f"--cov={module_name}"]}
        )
    if single_threaded:
        vscode.remove_settings(
            session,
            {
                "python.testing.pytestArgs": [
                    "--numprocesses auto",
                    "--numprocesses=auto",
                    "-n auto",
                    "-nauto",  # cspell:ignore nauto
                ]
            },
        )
    else:
        vscode.update_settings(
            session, {"python.testing.pytestArgs": ["--numprocesses=auto"]}
        )
        vscode.remove_settings(
            session,
            {
                "python.testing.pytestArgs": [
                    "--numprocesses auto",
                    "-n auto",
                    "-nauto",
                ]
            },
        )
    if not coverage_gutters:
        vscode.remove_settings(
            session,
            [
                "coverage-gutters.coverageFileNames",
                "coverage-gutters.coverageReportFileName",
                "coverage-gutters.showGutterCoverage",
                "coverage-gutters.showLineCoverage",
            ],
        )
