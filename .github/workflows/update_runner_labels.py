"""Refresh runner label types from GitHub's public image table."""

import ast
import re
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from textwrap import dedent
from urllib.request import urlopen

import typer

RUNNER_IMAGES_URL = (
    "https://raw.githubusercontent.com/actions/runner-images/main/README.md"
)


def main() -> None:
    """Update checked-in types and schema without network access during normal CLI use."""
    with urlopen(RUNNER_IMAGES_URL, timeout=30) as response:
        labels = parse_runner_labels(response.read().decode("utf-8"))
    root = Path(__file__).resolve().parents[2]
    target = root / "src/compwa_policy/config.py"
    target.write_text(update_runner_labels(target.read_text(), labels))
    subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            "-c",
            dedent("""
                from compwa_policy.cli._schema import SCHEMA_PATH, render_policy_schema

                SCHEMA_PATH.write_text(render_policy_schema())
            """),
        ],
        cwd=root,
        check=True,
    )


def parse_runner_labels(readme: str) -> dict[str, list[str]]:
    r'''Extract labels only from the available images table's YAML Label column.

    >>> from textwrap import dedent
    >>> readme = dedent("""
    ...     ## Available Images
    ...     | Image | YAML Label |
    ...     | macOS | `macos-26` or `macos-latest` |
    ...     | Linux | `ubuntu-26.04` |
    ...     ## Other
    ...     | Old | `ubuntu-old` |
    ... """)
    >>> parse_runner_labels(readme)
    {'macos': ['macos-26', 'macos-latest'], 'ubuntu': ['ubuntu-26.04']}
    '''
    section = readme.split("## Available Images\n", 1)[1].split("\n#", 1)[0]
    rows = [
        line.split("|")[1:-1] for line in section.splitlines() if line.startswith("|")
    ]
    column = next(i for i, cell in enumerate(rows[0]) if cell.strip() == "YAML Label")
    labels = {
        label for row in rows[1:] for label in re.findall(r"`([^`]+)`", row[column])
    }
    result = {
        platform: sorted(label for label in labels if label.startswith(f"{platform}-"))
        for platform in ("macos", "ubuntu")
    }
    if not all(result.values()):
        msg = "The runner image table must contain macOS and Ubuntu labels"
        raise ValueError(msg)
    return result


def update_runner_labels(config: str, labels: dict[str, list[str]]) -> str:
    r'''Replace the named label assignments while preserving all surrounding source.

    >>> from textwrap import dedent
    >>> config = dedent("""
    ...     # Keep this comment.
    ...     MacosRunnerLabel = Literal["old"]
    ...     "Supported macOS labels."
    ...     OTHER_SETTING = True
    ...     UbuntuRunnerLabel = Literal["old"]
    ... """)
    >>> updated = update_runner_labels(
    ...     config, {"macos": ["macos-26"], "ubuntu": ["ubuntu-26.04"]}
    ... )
    >>> print(updated)
    <BLANKLINE>
    # Keep this comment.
    MacosRunnerLabel = Literal[
        "macos-26",
    ]
    "Supported macOS labels."
    OTHER_SETTING = True
    UbuntuRunnerLabel = Literal[
        "ubuntu-26.04",
    ]
    <BLANKLINE>
    >>> update_runner_labels(
    ...     updated, {"macos": ["macos-26"], "ubuntu": ["ubuntu-26.04"]}
    ... ) == updated
    True
    >>> update_runner_labels("OTHER_SETTING = True", {"macos": ["macos-26"]})
    Traceback (most recent call last):
        ...
    ValueError: Expected exactly one assignment for MacosRunnerLabel
    '''
    assignments = [
        node for node in ast.parse(config).body if isinstance(node, ast.Assign)
    ]
    source = config.encode("utf-8")
    source_lines = source.splitlines(keepends=True)  # cspell:ignore keepends
    replacements: list[tuple[int, int, bytes]] = []
    for platform, values in labels.items():
        name = f"{platform.capitalize()}RunnerLabel"
        matches = [
            node
            for node in assignments
            if len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ]
        if len(matches) != 1:
            msg = f"Expected exactly one assignment for {name}"
            raise ValueError(msg)
        node = matches[0]
        if node.end_lineno is None or node.end_col_offset is None:
            msg = f"Missing source location for {name}"
            raise ValueError(msg)
        start = sum(map(len, source_lines[: node.lineno - 1])) + node.col_offset
        end = sum(map(len, source_lines[: node.end_lineno - 1])) + node.end_col_offset
        lines = [f"{name} = Literal["]
        lines.extend(f'    "{value}",' for value in values)
        lines.append("]")
        replacements.append((start, end, "\n".join(lines).encode("utf-8")))
    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source.decode("utf-8")


if __name__ == "__main__":
    typer.run(main)
