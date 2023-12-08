"""Check citation files."""

from __future__ import annotations

import json
import os
from textwrap import dedent

from html2text import HTML2Text
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import (
    FoldedScalarString,
    PreservedScalarString,
)

from repoma.errors import PrecommitError
from repoma.utilities import CONFIG_PATH, vscode
from repoma.utilities.executor import Executor
from repoma.utilities.precommit import (
    find_repo,
    load_round_trip_precommit_config,
    update_single_hook_precommit_repo,
)


def main() -> None:
    executor = Executor()
    if CONFIG_PATH.zenodo.exists():
        executor(convert_zenodo_json)
        executor(remove_zenodo_json)
    if CONFIG_PATH.citation.exists():
        if CONFIG_PATH.zenodo.exists():
            executor(remove_zenodo_json)
        executor(check_citation_keys)
        executor(add_json_schema_precommit)
        executor(vscode.add_extension_recommendation, "redhat.vscode-yaml")
        executor(update_vscode_settings)
    executor.finalize()


def convert_zenodo_json() -> None:
    with open(CONFIG_PATH.zenodo) as f:
        zenodo = json.load(f)
    citation_cff = _convert_zenodo(zenodo)
    _write_citation_cff(citation_cff)
    CONFIG_PATH.zenodo.unlink()
    msg = dedent(f"""
    Converted {CONFIG_PATH.zenodo} to a {CONFIG_PATH.citation} config
      For more info, see https://citation-file-format.github.io
    """).strip()
    raise PrecommitError(msg)


def remove_zenodo_json() -> None:
    CONFIG_PATH.zenodo.unlink()
    msg = (
        f"Removed {CONFIG_PATH.zenodo}, because a {CONFIG_PATH.citation} already exists"
    )
    raise PrecommitError(msg)


def _convert_zenodo(zenodo: dict) -> CommentedMap:
    citation_cff = CommentedMap(
        {
            "cff-version": "1.2.0",
            "message": "If you use this software, please cite it as below.",
            "title": FoldedScalarString(zenodo["title"]),
        }
    )

    description = zenodo.get("description")
    if description is not None:
        converter = HTML2Text()
        converter.body_width = None  # type: ignore[assignment]
        description = converter.handle(description).strip()
        citation_cff["abstract"] = PreservedScalarString(description)

    authors = _get_authors(zenodo)
    if authors is not None:
        citation_cff["authors"] = authors

    keywords = zenodo.get("keywords")
    if keywords is not None:
        citation_cff["keywords"] = keywords

    lic = zenodo.get("license")
    if lic is not None:
        citation_cff["license"] = lic

    return citation_cff


def _write_citation_cff(citation_cff: CommentedMap) -> None:
    newline_key = None
    for key in citation_cff:
        if key in {"cff-version", "message", "title", "abstract"}:
            continue
        newline_key = key
        break
    if newline_key is not None:
        citation_cff.yaml_set_comment_before_after_key(newline_key, before="\n")
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 88
    yaml.allow_unicode = True
    with open(CONFIG_PATH.citation, "w") as stream:
        yaml.dump(citation_cff, stream)


def _get_authors(zenodo: dict) -> list[dict[str, str]] | None:
    creators: list[dict[str, str]] | None = zenodo.get("creators")
    if creators is None:
        return None
    return [__convert_author(item) for item in creators]


def __convert_author(creator: dict) -> dict:
    full_name: str = creator["name"]
    family_name, *rest = full_name.split(",")
    if rest:
        given_names = " ".join(rest)
    else:
        words = full_name.split(" ")
        family_name = words[-1]
        given_names = " ".join(words[:-1])
    author_info = {
        "family-names": family_name.strip(),
        "given-names": given_names.strip(),
    }
    affiliation: str | None = creator.get("affiliation")
    if affiliation is not None:
        author_info["affiliation"] = affiliation
    orcid: str | None = creator.get("orcid")
    if orcid is not None:
        author_info["orcid"] = f"https://orcid.org/{orcid}"
    return author_info


def check_citation_keys() -> None:
    expected = {
        "cff-version",
        "title",
        "message",
        "abstract",
        "authors",
        "keywords",
        "license",
        "repository-code",
    }
    if os.path.exists("docs/"):
        expected.add("url")
    with open(CONFIG_PATH.citation) as f:
        yaml = YAML()
        citation_cff = yaml.load(f)
    if not citation_cff:
        msg = f"{CONFIG_PATH.citation} is empty"
        raise PrecommitError(msg)
    existing: set[str] = set(citation_cff)
    missing_keys = expected - existing
    if missing_keys:
        sorted_keys = sorted(missing_keys)
        msg = dedent(f"""
            {CONFIG_PATH.citation} is missing the following keys: {', '.join(sorted_keys)}
              More info on the keys can be found on
              https://github.com/citation-file-format/citation-file-format/blob/main/schema-guide.md#valid-keys
        """).strip()
        raise PrecommitError(msg)


def add_json_schema_precommit() -> None:
    if not CONFIG_PATH.citation.exists():
        return
    # cspell:ignore jsonschema schemafile
    expected_hook = CommentedMap(
        id="check-jsonschema",
        name="Check CITATION.cff",
        args=[
            "--default-filetype",
            "yaml",
            "--schemafile",
            "https://citation-file-format.github.io/1.2.0/schema.json",
            "CITATION.cff",
        ],
        pass_filenames=False,
    )
    config, yaml = load_round_trip_precommit_config()
    repo_url = "https://github.com/python-jsonschema/check-jsonschema"
    idx_and_repo = find_repo(config, repo_url)
    existing_repos: CommentedSeq = config["repos"]
    if idx_and_repo is None:
        repo = CommentedMap(
            repo=repo_url,
            hooks=[expected_hook],
        )
        update_single_hook_precommit_repo(repo)
    else:
        repo_idx, repo = idx_and_repo
        existing_hooks: CommentedSeq = repo["hooks"]
        hook_idx = None
        for i, hook in enumerate(existing_hooks):
            if hook == expected_hook:
                return
            if hook.get("name") == "Check CITATION.cff":
                hook_idx = i
        if hook_idx is None:
            existing_hooks.append(expected_hook)
        else:
            existing_hooks[hook_idx] = expected_hook
    existing_repos.yaml_set_comment_before_after_key(repo_idx + 1, before="\n")
    yaml.dump(config, CONFIG_PATH.precommit)
    msg = f"Updated check-jsonschema hook in {CONFIG_PATH.citation}"
    raise PrecommitError(msg)


def update_vscode_settings() -> None:
    vscode.update_settings(
        {
            "yaml.schemas": {
                "https://citation-file-format.github.io/1.2.0/schema.json": (
                    "CITATION.cff"
                )
            }
        },
    )
