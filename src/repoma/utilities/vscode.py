"""Helper functions for modifying a VSCode configuration."""

import json

from repoma.errors import PrecommitError

from . import CONFIG_PATH


def add_vscode_extension_recommendation(extension_name: str) -> None:
    if not CONFIG_PATH.vscode_extensions.exists():
        CONFIG_PATH.vscode_extensions.parent.mkdir(exist_ok=True)
        config = {}
    else:
        with open(CONFIG_PATH.vscode_extensions) as stream:
            config = json.load(stream)
    recommended_extensions = config.get("recommendations", [])
    if extension_name not in set(recommended_extensions):
        recommended_extensions.append(extension_name)
        config["recommendations"] = recommended_extensions
        __dump_vscode_config(config)
        raise PrecommitError(
            f'Added VSCode extension recommendation "{extension_name}"'
        )


def remove_vscode_extension_recommendation(extension_name: str) -> None:
    if not CONFIG_PATH.vscode_extensions.exists():
        return
    with open(CONFIG_PATH.vscode_extensions) as stream:
        config = json.load(stream)
    recommended_extensions = list(config.get("recommendations", []))
    if extension_name in recommended_extensions:
        recommended_extensions.remove(extension_name)
        config["recommendations"] = recommended_extensions
        __dump_vscode_config(config)
        raise PrecommitError(
            f'Removed VSCode extension recommendation "{extension_name}"'
        )


def __dump_vscode_config(config: dict) -> None:
    with open(CONFIG_PATH.vscode_extensions, "w") as stream:
        json.dump(config, stream, indent=2, sort_keys=True)
        stream.write("\n")
