"""Helper functions for modifying a VSCode configuration."""

import json
from pathlib import Path
from typing import Iterable

from repoma.errors import PrecommitError

from . import CONFIG_PATH


def remove_settings(keys: Iterable[str]) -> None:
    removed_keys = set(keys)
    settings = __load_config(CONFIG_PATH.vscode_settings, create=True)
    new_settings = {k: v for k, v in settings.items() if k not in removed_keys}
    _update_settings(settings, new=new_settings)


def set_setting(values: dict) -> None:
    settings = __load_config(CONFIG_PATH.vscode_settings, create=True)
    _update_settings(settings, new={**settings, **values})


def _update_settings(old: dict, new: dict) -> None:
    if old == new:
        return
    __dump_config(new, CONFIG_PATH.vscode_settings)
    raise PrecommitError("Updated VS Code settings")


def remove_unwanted_recommendations() -> None:
    if not CONFIG_PATH.vscode_extensions.exists():
        return
    config = __load_config(CONFIG_PATH.vscode_extensions)
    key = "unwantedRecommendations"
    unwanted_recommendations = config.pop(key, None)
    if unwanted_recommendations is not None:
        __dump_config(config, CONFIG_PATH.vscode_extensions)
        raise PrecommitError(f'Removed VS Code extension setting "{key}"')


def add_extension_recommendation(extension_name: str) -> None:
    config = __load_config(CONFIG_PATH.vscode_extensions, create=True)
    recommended_extensions = config.get("recommendations", [])
    if extension_name not in set(recommended_extensions):
        recommended_extensions.append(extension_name)
        config["recommendations"] = sorted(recommended_extensions)
        __dump_config(config, CONFIG_PATH.vscode_extensions)
        raise PrecommitError(
            f'Added VS Code extension recommendation "{extension_name}"'
        )


def remove_extension_recommendation(extension_name: str) -> None:
    if not CONFIG_PATH.vscode_extensions.exists():
        return
    with open(CONFIG_PATH.vscode_extensions) as stream:
        config = json.load(stream)
    recommended_extensions = list(config.get("recommendations", []))
    if extension_name in recommended_extensions:
        recommended_extensions.remove(extension_name)
        config["recommendations"] = sorted(recommended_extensions)
        __dump_config(config, CONFIG_PATH.vscode_extensions)
        raise PrecommitError(
            f'Removed VS Code extension recommendation "{extension_name}"'
        )


def __dump_config(config: dict, path: Path) -> None:
    with open(path, "w") as stream:
        json.dump(config, stream, indent=2, sort_keys=True)
        stream.write("\n")


def __load_config(path: Path, create: bool = False) -> dict:
    if not path.exists() and create:
        path.parent.mkdir(exist_ok=True)
        return {}
    with open(path) as stream:
        return json.load(stream)
