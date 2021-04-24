import os
from configparser import ConfigParser

import yaml

import repoma
from repoma.pre_commit_hooks.errors import PrecommitError

REPOMA_DIR = os.path.dirname(repoma.__file__)


def add_badge(badge_line: str) -> None:
    readme_path = "README.md"
    if not os.path.exists("README.md"):
        raise PrecommitError(
            f'This repository contains no "{readme_path}", so cannot add badge'
        )
    with open(readme_path) as stream:
        lines = stream.readlines()
    expected_badge = badge_line
    if expected_badge not in lines:
        error_message = f'"{readme_path}" is missing a badge:\n'
        error_message += f"  {badge_line}"
        insert_position = 0
        for insert_position, line in enumerate(lines):  # noqa: B007
            if line.startswith("#"):  # find first Markdown section
                break
        if len(lines) == 0 or insert_position == len(lines) - 1:
            error_message += (
                f'"{readme_path}" contains no title, so cannot add badge'
            )
            raise PrecommitError(error_message)
        lines.insert(insert_position + 1, f"\n{expected_badge}")
        with open(readme_path, "w") as stream:
            stream.writelines(lines)
        error_message += "Problem has been fixed."
        raise PrecommitError(error_message)


def check_has_file(path: str) -> None:
    if not os.path.exists(path) and not os.path.exists("cspell.json"):
        raise PrecommitError(f"This repository contains no {path} config file")


def get_repo_url() -> str:
    setup_file = "setup.cfg"
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
    project_urls = dict()
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
