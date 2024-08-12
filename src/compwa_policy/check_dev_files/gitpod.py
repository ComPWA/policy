"""Extract :code:`.gitpod.yml` file from :code:`launch.json`."""

import json
import os

import yaml

from compwa_policy.errors import PrecommitError
from compwa_policy.utilities import COMPWA_POLICY_DIR, CONFIG_PATH
from compwa_policy.utilities.pyproject import (
    Pyproject,
    PythonVersion,
    get_constraints_file,
)
from compwa_policy.utilities.readme import add_badge, remove_badge
from compwa_policy.utilities.yaml import write_yaml


def main(no_gitpod: bool, python_version: PythonVersion) -> None:
    if no_gitpod:
        if CONFIG_PATH.gitpod.exists():
            os.remove(CONFIG_PATH.gitpod)
            msg = f"Removed {CONFIG_PATH.gitpod} as requested by --no-gitpod"
            raise PrecommitError(msg)
        remove_badge(r"\[!\[GitPod\]\(https://img.shields.io/badge/gitpod")
        return
    error_message = ""
    expected_config = _generate_gitpod_config(python_version)
    if CONFIG_PATH.gitpod.exists():
        with open(CONFIG_PATH.gitpod) as stream:
            existing_config = yaml.load(stream, Loader=yaml.SafeLoader)
        if existing_config != expected_config:
            error_message = "GitPod config does not have expected content"
    else:
        error_message = f"GitPod config {CONFIG_PATH.gitpod} does not exist"
    if error_message:
        write_yaml(expected_config, output_path=CONFIG_PATH.gitpod)
        error_message += ". Problem has been fixed."
        raise PrecommitError(error_message)
    try:
        repo_url = Pyproject.load().get_repo_url()
        add_badge(
            f"[![GitPod](https://img.shields.io/badge/gitpod-open-blue?logo=gitpod)](https://gitpod.io/#{repo_url})"
        )
    except PrecommitError:
        pass


def _extract_extensions() -> dict:
    if CONFIG_PATH.vscode_extensions.exists():
        with open(CONFIG_PATH.vscode_extensions) as stream:
            return json.load(stream)["recommendations"]
    return {}


def _generate_gitpod_config(python_version: PythonVersion) -> dict:
    with open(COMPWA_POLICY_DIR / ".template" / CONFIG_PATH.gitpod) as stream:
        gitpod_config = yaml.load(stream, Loader=yaml.SafeLoader)
    tasks = gitpod_config["tasks"]
    tasks[0]["init"] = f"pyenv local {python_version}"
    constraints_file = get_constraints_file(python_version)
    if constraints_file is None:
        tasks[1]["init"] = "pip install -e .[dev]"
    else:
        tasks[1]["init"] = f"pip install -c {constraints_file} -e .[dev]"
    extensions = _extract_extensions()
    if extensions:
        gitpod_config["vscode"] = {"extensions": extensions}
    return gitpod_config
