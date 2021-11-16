from repoma.check_dev_files.github_templates import _list_template_files
from repoma.utilities import REPOMA_DIR


def test_list_issue_templates():
    files = _list_template_files(REPOMA_DIR / ".github/ISSUE_TEMPLATE")
    assert set(files) == {
        "bug_report.md",
        "feature_request.md",
    }
