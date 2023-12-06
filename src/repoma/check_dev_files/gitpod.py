"""Extract :code:`.gitpod.yml` file from :code:`launch.json`."""

import json
import os
from pathlib import Path

import yaml

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR
from repoma.utilities.project_info import PythonVersion, get_repo_url
from repoma.utilities.readme import add_badge
from repoma.utilities.yaml import write_yaml


def main(no_gitpod: bool, python_version: PythonVersion) -> None:
    if no_gitpod:
        if CONFIG_PATH.gitpod.exists():
            os.remove(CONFIG_PATH.gitpod)
            msg = f"Removed {CONFIG_PATH.gitpod} as requested by --no-gitpod"
            raise PrecommitError(msg)
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
        repo_url = get_repo_url()
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
    with open(REPOMA_DIR / ".template" / CONFIG_PATH.gitpod) as stream:
        gitpod_config = yaml.load(stream, Loader=yaml.SafeLoader)
    tasks = gitpod_config["tasks"]
    constraints = __get_constraints_file(python_version)
    if constraints.exists():
        tasks[0]["init"] = f"pip install -c {constraints} -e .[dev]"
        tasks[1]["init"] = f"pip install -c {constraints} -e .[dev]"
    else:
        tasks[0]["init"] = f"pyenv local {python_version}"
        tasks[1]["init"] = "pip install -e .[dev]"
    extensions = _extract_extensions()
    if extensions:
        gitpod_config["vscode"] = {"extensions": extensions}
    return gitpod_config


def __get_constraints_file(python_version: PythonVersion) -> Path:
    return Path(f".constraints/py{python_version}.txt")
