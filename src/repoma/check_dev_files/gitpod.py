"""Extract :code:`.gitpod.yml` file from :code:`launch.json`."""

import json
import os

import yaml

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, REPOMA_DIR
from repoma.utilities.readme import add_badge
from repoma.utilities.setup_cfg import get_repo_url
from repoma.utilities.yaml import write_yaml

__CONSTRAINTS_FILE = ".constraints/py3.8.txt"


def main() -> None:
    pin_dependencies = os.path.exists(__CONSTRAINTS_FILE)
    error_message = ""
    expected_config = _generate_gitpod_config(pin_dependencies)
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
            # pylint: disable=line-too-long
            f"[![GitPod](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#{repo_url})"
        )
    except PrecommitError:
        pass


def _extract_extensions() -> dict:
    if CONFIG_PATH.vscode_extensions.exists():
        with open(CONFIG_PATH.vscode_extensions) as stream:
            return json.load(stream)["recommendations"]
    return {}


def _generate_gitpod_config(pin_dependencies: bool) -> dict:
    with open(REPOMA_DIR / ".template" / CONFIG_PATH.gitpod) as stream:
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
