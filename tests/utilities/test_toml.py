from __future__ import annotations

from textwrap import dedent

import pytest
import tomlkit

from compwa_policy.utilities.toml import (
    to_inline_table,
    to_multiline_string,
    to_toml_array,
)


def _dump(array):
    return tomlkit.dumps({"a": array}).strip()


def describe_to_inline_table():
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ({}, "a = {}"),
            ({"type": "simple"}, 'a = { type = "simple" }'),
            (
                {"name": "path", "positional": True},
                'a = { name = "path", positional = true }',
            ),
        ],
    )
    def renders_with_tombi_spacing(value: dict, expected: str):
        assert _dump(to_inline_table(value)) == expected


def describe_to_multiline_string():
    def has_the_same_value_after_serialization():
        value = "\nline one\nline two\n"
        string = to_multiline_string(value)

        parsed_again = tomlkit.loads(tomlkit.dumps({"value": string}))["value"]

        assert string == parsed_again


def describe_to_toml_array():
    def renders_empty_array():
        array = to_toml_array([])
        assert _dump(array) == "a = []"

    def renders_single_item():
        lst = [1]
        array = to_toml_array(lst)
        assert _dump(array) == "a = [1]"

        array = to_toml_array(lst, multiline=True)
        expected = dedent("""
            a = [
                1,
            ]
        """)
        assert _dump(array) == expected.strip()

    @pytest.mark.parametrize(
        ("lst", "multiline", "expected"),
        [
            ([0], False, "a = [0]"),
            (
                [0],
                True,
                """
                a = [
                    0,
                ]
                """,
            ),
            ([0], None, "a = [0]"),
            ([1, 2, 3], False, "a = [1, 2, 3]"),
            (
                [1, 2, 3],
                True,
                """
                a = [
                    1,
                    2,
                    3,
                ]
                """,
            ),
            (
                [1, 2, 3],
                None,
                """
                a = [
                    1,
                    2,
                    3,
                ]
                """,
            ),
        ],
    )
    def renders_multiple_items(lst: list[int], multiline: bool, expected: str):
        array = to_toml_array(lst, multiline)
        expected = dedent(expected).strip()
        assert _dump(array) == expected.strip()
