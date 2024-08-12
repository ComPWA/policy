from textwrap import dedent

import pytest

from compwa_policy.check_dev_files.pixi import _update_docnb_and_doclive
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.pyproject import ModifiablePyproject


@pytest.mark.parametrize(
    "table_key",
    [
        "tool.pixi.feature.dev.tasks",
        "tool.pixi.tasks",
    ],
)
def test_update_docnb_and_doclive(table_key: str):
    content = dedent(f"""
        [{table_key}.doc]
        cmd = "command executed by doc"

        [{table_key}.docnb]
        cmd = "some outdated command"

        [{table_key}.docnb-test]
        cmd = "should not change"
    """)
    with pytest.raises(
        PrecommitError,
        match="Updated `cmd` of Pixi tasks docnb",
    ), ModifiablePyproject.load(content) as pyproject:
        _update_docnb_and_doclive(pyproject, table_key)
    new_content = pyproject.dumps()
    expected = dedent(f"""
        [{table_key}.doc]
        cmd = "command executed by doc"

        [{table_key}.docnb]
        cmd = "command executed by doc"

        [{table_key}.docnb-test]
        cmd = "should not change"
    """)
    assert new_content.strip() == expected.strip()
