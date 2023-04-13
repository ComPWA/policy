"""Check `flake8 <https://flake8.pycqa.org>`_ configuration."""

import io
import re
from configparser import ConfigParser
from textwrap import dedent, indent
from typing import Iterable, Optional

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, natural_sorting
from repoma.utilities.cfg import extract_config_section, format_config, open_config
from repoma.utilities.executor import Executor
from repoma.utilities.setup_cfg import open_setup_cfg

# cspell:ignore fstring
__FLAKE8_REQUIREMENTS = [
    "flake8 >=4",
    "flake8-blind-except",
    "flake8-bugbear",
    "flake8-builtins",
    "flake8-comprehensions",
    "flake8-pytest-style",
    "flake8-rst-docstrings",
    "flake8-type-ignore",
    "flake8-use-fstring",
    "pep8-naming",
]


def main() -> None:
    if not _is_flake8_installed():
        return
    executor = Executor()
    executor(_extract_flake8_config)
    executor(_check_config_exists)
    executor(_format_flake8_config)
    executor(_check_comments_on_separate_line)
    executor(_check_option_order)
    executor(_check_setup_cfg)
    executor(
        _check_missing_options,
        option="extend-select",
        expected_values=[
            "TI100",
        ],
    )
    executor(
        _check_missing_options,
        option="ignore",
        expected_values=[
            "TI1",
        ],
    )
    executor.finalize()


def _is_flake8_installed() -> bool:
    cfg = open_setup_cfg()
    for _, value in cfg.items("options.extras_require"):
        if "flake8" in value:
            return True
    return False


def _extract_flake8_config() -> None:
    """Attempt to extract a :file:`.flake8` from :file:`setup.cfg/tox.ini`.

    See https://flake8.pycqa.org/en/latest/user/configuration.html.
    """
    extract_config_section(
        extract_from=CONFIG_PATH.setup_cfg,
        extract_to=CONFIG_PATH.flake8,
        sections=["flake8"],
    )
    extract_config_section(
        extract_from=CONFIG_PATH.tox,
        extract_to=CONFIG_PATH.flake8,
        sections=["flake8"],
    )


def _check_config_exists() -> None:
    if not CONFIG_PATH.flake8.exists():
        raise PrecommitError(
            f"This repository has no {CONFIG_PATH.flake8} config file."
        )


def _format_flake8_config() -> None:
    format_config(
        input=".flake8",
        output=".flake8",
        additional_rules=[
            _move_comments_before_line,
        ],
    )


def _move_comments_before_line(content: str) -> str:
    return re.sub(
        r"\n([^\S\r\n]*)([A-Za-z][^#^\n]+)  # ([^\n]+)\n",
        r"\n\1# \3\n\1\2\n",
        content,
    )


def _check_comments_on_separate_line(
    input: Optional[io.StringIO] = None,  # noqa: A002
) -> None:
    if input is None:
        with open(CONFIG_PATH.flake8) as stream:
            lines = stream.readlines()
    else:
        lines = input.readlines()
    for line in lines:
        split_line = [s.strip() for s in line.split("#")]
        if len(split_line) == 1:
            continue
        before_comment = split_line[0]
        if before_comment:
            raise PrecommitError(
                "Please move the comment on the following line in the"
                f" {CONFIG_PATH.flake8} config file to a separate line:\n\n"
                f"    {line}\n\n"
                "For more info, see "
                "https://flake8.pycqa.org/en/latest/user/configuration.html#project-configuration"
            )


def _check_option_order(cfg: Optional[ConfigParser] = None) -> None:
    if cfg is None:
        cfg = open_config(CONFIG_PATH.flake8)
    for section in cfg.sections():
        for option, content in cfg.items(section):
            values = content.split("\n")
            if "" in values:
                values.remove("")
            if values != sorted(values, key=lambda s: natural_sorting(s.lower())):
                raise PrecommitError(
                    f'Option "{option}" in section [{section}] is not sorted'
                )


def _check_setup_cfg(cfg: Optional[ConfigParser] = None) -> None:
    if cfg is None:
        cfg = open_setup_cfg()
    extras_require = "options.extras_require"
    if not cfg.has_section(extras_require):
        raise PrecommitError(
            f"Please list flake8 under a section [{extras_require}] in setup.cfg"
        )
    requirements = indent("\n".join(__FLAKE8_REQUIREMENTS), 12 * " ")
    error_message = f"""\
        Section [{extras_require}] in setup.cfg should look like this:

        [{extras_require}]
        ...
        flake8 =\n{requirements}
        ...
        lint =
            %(flake8)s
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
    error_message = dedent(error_message).strip()
    if not cfg.has_option(extras_require, "flake8"):
        raise PrecommitError(error_message)
    packages = cfg.get(extras_require, "flake8").split("\n")
    if "" in packages:
        packages.remove("")
    packages = [p.split(";")[0].strip() for p in packages]
    packages = [p.split("#")[0].strip() for p in packages]
    if not set(__FLAKE8_REQUIREMENTS) <= set(packages):
        raise PrecommitError(error_message)


def _check_missing_options(
    option: str,
    expected_values: Iterable[str],
    cfg: Optional[ConfigParser] = None,
) -> None:
    if cfg is None:
        cfg = open_config(CONFIG_PATH.flake8)
    content = ""
    if cfg.has_option("flake8", option):
        content = cfg.get("flake8", option)
    missing_values = []
    for value in expected_values:
        if not re.search(rf"\b{value}\b", content):
            missing_values.append(value)
    if missing_values:
        values = "\n".join(missing_values)
        raise PrecommitError(dedent(f"""
            Flake8 config is missing an option. Expecting:

            [flake8]
            {option} =
                ...
                {values}
                ...
            """).strip())
