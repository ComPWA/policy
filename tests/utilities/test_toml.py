from __future__ import annotations

from textwrap import dedent

import pytest
import tomlkit

from compwa_policy.utilities.toml import to_toml_array


def test_to_toml_array_empty():
    array = to_toml_array([])
    assert _dump(array) == "a = []"


def test_to_toml_array_single_item():
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
def test_to_toml_array_multiple_items(lst: list[int], multiline: bool, expected: str):
    array = to_toml_array(lst, multiline)
    expected = dedent(expected).strip()
    assert _dump(array) == expected.strip()


def _dump(array):
    return tomlkit.dumps({"a": array}).strip()
