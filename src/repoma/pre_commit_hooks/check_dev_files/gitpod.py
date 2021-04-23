"""Extract :code:`.gitpod.yml` file from :code:`launch.json`."""

import json
import os

import yaml

from repoma.pre_commit_hooks.errors import PrecommitError

from ._helpers import REPOMA_DIR, write_yaml

__CONSTRAINTS_FILE = ".constraints/py3.8.txt"
__EXTENSIONS_FILE = ".vscode/extensions.json"
__GITPOD_CONFIG_FILE = ".gitpod.yml"


def check_gitpod_config() -> None:
    pin_dependencies = os.path.exists(__CONSTRAINTS_FILE)
    error_message = ""
    expected_config = _generate_gitpod_config(pin_dependencies)
    if os.path.exists(__GITPOD_CONFIG_FILE):
        with open(__GITPOD_CONFIG_FILE) as stream:
            existing_config = yaml.load(stream, Loader=yaml.SafeLoader)
        if existing_config != expected_config:
            error_message = "GitPod config does not have expected content"
    else:
        error_message = f"GitPod config {__GITPOD_CONFIG_FILE} does not exist"
    if error_message:
        write_yaml(expected_config, output_path=__GITPOD_CONFIG_FILE)
        error_message += ". Problem has been fixed."
        raise PrecommitError(error_message)


def _extract_extensions() -> dict:
    if os.path.exists(__EXTENSIONS_FILE):
        with open(__EXTENSIONS_FILE) as stream:
            return json.load(stream)["recommendations"]
    return dict()


def _generate_gitpod_config(pin_dependencies: bool) -> dict:
    with open(f"{REPOMA_DIR}/{__GITPOD_CONFIG_FILE}") as stream:
        gitpod_config = yaml.load(stream, Loader=yaml.SafeLoader)
    tasks = gitpod_config["tasks"]
    if pin_dependencies:
        tasks[0]["init"] = f"pip install -c {__CONSTRAINTS_FILE} -e .[dev]"
    else:
        tasks[0]["init"] = "pip install -e .[dev]"
    extensions = _extract_extensions()
    if extensions:
        gitpod_config["vscode"] = {"extensions": extensions}
    return gitpod_config
