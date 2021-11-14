"""Check :file:`pyproject.toml` black config."""

from collections import OrderedDict
from textwrap import dedent
from typing import TYPE_CHECKING

import toml

from repoma._utilities import (
    CONFIG_PATH,
    get_supported_python_versions,
    natural_sorting,
)
from repoma.errors import PrecommitError

if TYPE_CHECKING:
    from typing import Optional


def main() -> None:
    if not CONFIG_PATH.pyproject.exists():
        return
    config = _load_config()
    _check_line_length(config)
    _check_experimental_string_processing(config)
    _check_option_ordering(config)
    _check_target_versions(config)


def _load_config(content: "Optional[str]" = None) -> dict:
    if content is None:
        with open(CONFIG_PATH.pyproject) as stream:
            config = toml.load(stream, _dict=OrderedDict)
    else:
        config = toml.loads(content, _dict=OrderedDict)
    return config.get("tool", {}).get("black")


def _check_experimental_string_processing(config: dict) -> None:
    expected_option = "experimental-string-processing"
    if config.get(expected_option) is not True:
        raise PrecommitError(
            dedent(
                f"""
            An option in pyproject.toml is wrong or missing. Should be:

            [tool.black]
            {expected_option} = true
            """
            ).strip()
        )


def _check_line_length(config: dict) -> None:
    expected_line_length = 79
    if config.get("line-length") != expected_line_length:
        raise PrecommitError(
            dedent(
                f"""
            Black line-length in pyproject.toml in pyproject.toml should be:

            [tool.black]
            line-length = {expected_line_length}
            """
            ).strip()
        )


def _check_option_ordering(config: dict) -> None:
    options = list(config)
    sorted_options = sorted(config, key=natural_sorting)
    if sorted_options != options:
        error_message = dedent(
            """
            Options in pyproject.toml should be alphabetically sorted:

            [tool.black]
            """
        ).strip()
        for option in sorted_options:
            error_message += f"\n{option} = ..."
        raise PrecommitError(error_message)


def _check_target_versions(config: dict) -> None:
    target_versions = config.get("target-version", [])
    supported_python_versions = get_supported_python_versions()
    expected_target_versions = sorted(
        map(lambda s: "py" + s.replace(".", ""), supported_python_versions)
    )
    if "py310" in expected_target_versions:
        expected_target_versions.remove("py310")
    if target_versions != expected_target_versions:
        error_message = dedent(
            """
            Black target versions in pyproject.toml should be as follows:

            [tool.black]
            target-version = [
            """
        ).strip()
        for version in expected_target_versions:
            error_message += f"\n    '{version}',"
        error_message += "\n]"
        raise PrecommitError(error_message)
