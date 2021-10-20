import io
import json
import os
import re
from configparser import ConfigParser
from typing import Any, Dict, List, NamedTuple, Optional

import yaml

import repoma
from repoma.pre_commit_hooks.errors import PrecommitError


class ConfigFilePaths(NamedTuple):
    cspell: str = ".cspell.json"
    editor_config: str = ".editorconfig"
    pre_commit: str = ".pre-commit-config.yaml"
    prettier: str = ".prettierrc"
    prettier_ignore: str = ".prettierignore"
    setup_cfg: str = "setup.cfg"
    tox: str = "tox.ini"
    vscode_extensions: str = ".vscode/extensions.json"
    gitpod: str = ".gitpod.yml"


CONFIG_PATH = ConfigFilePaths()

REPOMA_DIR = os.path.dirname(repoma.__file__)
__README_PATH = "README.md"


def add_badge(badge: str) -> None:
    if not os.path.exists(__README_PATH):
        raise PrecommitError(
            f'This repository contains no "{__README_PATH}", so cannot add badge'
        )
    with open(__README_PATH) as stream:
        lines = stream.readlines()
    stripped_lines = set(map(lambda s: s.strip("\n"), lines))
    stripped_lines = set(map(lambda s: s.strip("<br>"), stripped_lines))
    stripped_lines = set(map(lambda s: s.strip("<br />"), stripped_lines))
    if badge not in stripped_lines:
        error_message = f'"{__README_PATH}" is missing a badge:\n'
        error_message += f"  {badge}\n"
        insert_position = 0
        for insert_position, line in enumerate(lines):  # noqa: B007
            if line.startswith("#"):  # find first Markdown section
                break
        if len(lines) == 0 or insert_position == len(lines) - 1:
            error_message += (
                f'"{__README_PATH}" contains no title, so cannot add badge'
            )
            raise PrecommitError(error_message)
        lines.insert(insert_position + 1, f"\n{badge}")
        with open(__README_PATH, "w") as stream:
            stream.writelines(lines)
        error_message += "Problem has been fixed."
        raise PrecommitError(error_message)


def remove_badge(badge_pattern: str) -> None:
    if not os.path.exists(__README_PATH):
        raise PrecommitError(
            f'This repository contains no "{__README_PATH}", so cannot add badge'
        )
    with open(__README_PATH) as stream:
        lines = stream.readlines()
    badge_line = None
    for line in lines:
        if re.match(badge_pattern, line):
            badge_line = line
            break
    if badge_line is None:
        return
    lines.remove(badge_line)
    with open(__README_PATH, "w") as stream:
        stream.writelines(lines)
    raise PrecommitError(
        f'A badge has been removed from "{__README_PATH}":\n\n'
        f"  {badge_line}"
    )


def copy_config(cfg: ConfigParser) -> ConfigParser:
    # can't use deepcopy in Python 3.6
    # https://stackoverflow.com/a/24343297
    stream = io.StringIO()
    cfg.write(stream)
    stream.seek(0)
    cfg_copy = ConfigParser()
    cfg_copy.read_file(stream)
    return cfg_copy


def find_precommit_hook(search_pattern: str) -> Optional[Dict[str, Any]]:
    """Find repo definition from .pre-commit-config.yaml.

    >>> repo = find_precommit_hook(r".*pre-commit/mirrors-prettier")
    >>> repo["hooks"]
    [{'id': 'prettier'}]
    >>> find_precommit_hook("non-existent")
    """
    precommit_repos = get_precommit_repos()
    for repo in precommit_repos:
        url = repo.get("repo")
        if url is None:
            continue
        if re.match(search_pattern, url):
            return repo
    return None


def get_precommit_repos() -> List[Dict[str, Any]]:
    if not os.path.exists(CONFIG_PATH.pre_commit):
        raise PrecommitError(
            "Are you sure this repository contains a"
            f' "./{CONFIG_PATH.pre_commit}" file?'
        )
    with open(CONFIG_PATH.pre_commit) as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
    repos = config.get("repos")
    if repos is None:
        raise PrecommitError(
            f'"./{CONFIG_PATH.pre_commit}" does not contain a "repos" section'
        )
    return repos


def get_repo_url() -> str:
    setup_file = CONFIG_PATH.setup_cfg
    if not os.path.exists(setup_file):
        raise PrecommitError("This repository contains no setup.cfg file")
    cfg = ConfigParser()
    cfg.read(setup_file)
    if not cfg.has_section("metadata"):
        raise PrecommitError("setup.cfg does not contain a metadata section")
    project_urls_def = cfg["metadata"].get("project_urls", None)
    if project_urls_def is None:
        error_message = (
            "Section metadata in setup.cfg does not contain project_urls."
            " Should be something like:\n\n"
            "[metadata]\n"
            "...\n"
            "project_urls =\n"
            "    Tracker = https://github.com/ComPWA/ampform/issues\n"
            "    Source = https://github.com/ComPWA/ampform\n"
            "    ...\n"
        )
        raise PrecommitError(error_message)
    project_url_lines = project_urls_def.split("\n")
    project_url_lines = list(
        filter(lambda line: line.strip(), project_url_lines)
    )
    project_urls = {}
    for line in project_url_lines:
        url_type, url, *_ = tuple(line.split("="))
        url_type = url_type.strip()
        url = url.strip()
        project_urls[url_type] = url
    source_url = project_urls.get("Source")
    if source_url is None:
        raise PrecommitError(
            'metadata.project_urls in setup.cfg does not contain "Source" URL'
        )
    return source_url


def rename_config(old: str, new: str) -> None:
    if os.path.exists(old):
        os.rename(old, new)
        raise PrecommitError(f"File {old} has been renamed to {new}")


def add_vscode_extension_recommendation(extension_name: str) -> None:
    if not os.path.exists(CONFIG_PATH.vscode_extensions):
        os.makedirs(
            os.path.dirname(CONFIG_PATH.vscode_extensions), exist_ok=True
        )
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
    if not os.path.exists(CONFIG_PATH.vscode_extensions):
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


def write_script(content: str, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as stream:
        stream.write(content)


class _IncreasedYamlIndent(yaml.Dumper):
    # pylint: disable=too-many-ancestors
    def increase_indent(self, flow=False, indentless=False):  # type: ignore
        return super().increase_indent(flow, False)

    def write_line_break(self, data=None):  # type: ignore
        """See https://stackoverflow.com/a/44284819."""
        super().write_line_break(data)
        if len(self.indents) == 1:
            super().write_line_break()


def write_yaml(definition: dict, output_path: str) -> None:
    """Write a `dict` to disk with standardized YAML formatting."""
    with open(output_path, "w") as stream:
        yaml.dump(
            definition,
            stream,
            sort_keys=False,
            Dumper=_IncreasedYamlIndent,
            default_flow_style=False,
        )
