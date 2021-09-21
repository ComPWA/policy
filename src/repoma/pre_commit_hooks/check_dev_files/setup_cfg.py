"""Apply a certain set of standards to the :file:`setup.cfg`."""

import os
import textwrap
from collections import defaultdict
from copy import deepcopy

from repoma.pre_commit_hooks.errors import PrecommitError
from repoma.pre_commit_hooks.format_setup_cfg import (
    SETUP_CFG_PATH,
    open_setup_cfg,
    write_formatted_setup_cfg,
)


def fix_setup_cfg() -> None:
    if not os.path.exists(SETUP_CFG_PATH):
        return
    _check_required_options()
    _update_author_data()
    _fix_long_description()


def _check_required_options() -> None:
    cfg = open_setup_cfg()
    required_options = {
        "metadata": [
            "name",
            "description",
            "license",
            "classifiers",
        ],
        "options": ["python_requires"],
    }
    missing_options = defaultdict(list)
    for section, options in required_options.items():
        for option in options:
            if cfg.has_option(section, option):
                continue
            missing_options[section].append(option)
    if missing_options:
        summary = "\n"
        for section, options in missing_options.items():
            summary += f"[{section}]\n...\n"
            for option in options:
                summary += f"{option} = ...\n"
            summary += "...\n"
        raise PrecommitError(
            f"./{SETUP_CFG_PATH} is missing the following options:\n"
            + textwrap.indent(summary, prefix="  ")
        )


def _update_author_data() -> None:
    old_cfg = open_setup_cfg()
    new_cfg = deepcopy(old_cfg)
    new_cfg.set("metadata", "author", "Common Partial Wave Analysis")
    new_cfg.set("metadata", "author_email", "Common Partial Wave Analysis")
    new_cfg.set("metadata", "author_email", "compwa-admin@ep1.rub.de")
    if new_cfg != old_cfg:
        write_formatted_setup_cfg(new_cfg)
        raise PrecommitError(f"Updated author info in ./{SETUP_CFG_PATH}")


def _fix_long_description() -> None:
    if os.path.exists("README.md"):
        old_cfg = open_setup_cfg()
        new_cfg = deepcopy(old_cfg)
        new_cfg.set("metadata", "long_description", "file: README.md")
        new_cfg.set(
            "metadata", "long_description_content_type", "text/markdown"
        )
        if new_cfg != old_cfg:
            write_formatted_setup_cfg(new_cfg)
            raise PrecommitError(
                f"Updated long_description in ./{SETUP_CFG_PATH}"
            )
