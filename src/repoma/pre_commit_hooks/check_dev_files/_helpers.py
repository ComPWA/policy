from os.path import dirname, exists

import yaml

import repoma
from repoma.pre_commit_hooks.errors import PrecommitError

REPOMA_DIR = dirname(repoma.__file__)


def check_has_file(path: str) -> None:
    if not exists(path) and not exists("cspell.json"):
        raise PrecommitError(f"This repository contains no {path} config file")


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
