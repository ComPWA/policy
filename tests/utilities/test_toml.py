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

    array = to_toml_array(lst, enforce_multiline=True)
    expected = dedent("""
        a = [
            1,
        ]
    """)
    assert _dump(array) == expected.strip()


@pytest.mark.parametrize("enforce_multiline", [False, True])
def test_to_toml_array_multiple_items(enforce_multiline: bool):
    lst = [1, 2, 3]
    array = to_toml_array(lst, enforce_multiline)
    expected = dedent("""
        a = [
            1,
            2,
            3,
        ]
    """)
    assert _dump(array) == expected.strip()


def _dump(array):
    return tomlkit.dumps({"a": array}).strip()
