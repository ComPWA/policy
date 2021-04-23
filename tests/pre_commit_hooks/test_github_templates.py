from repoma.pre_commit_hooks.check_dev_files._helpers import REPOMA_DIR
from repoma.pre_commit_hooks.check_dev_files.github_templates import (
    _list_template_files,
)


def test_list_issue_templates():
    assert _list_template_files(f"{REPOMA_DIR}/.github/ISSUE_TEMPLATE") == [
        "bug_report.md",
        "feature_request.md",
    ]
