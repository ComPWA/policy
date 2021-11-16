from repoma.utilities.setup_cfg import open_setup_cfg


def test_open_setup_cfg():
    cfg = open_setup_cfg()
    sections = cfg.sections()
    assert sections == [
        "metadata",
        "options",
        "options.extras_require",
        "options.entry_points",
        "options.packages.find",
        "options.package_data",
    ]
    assert cfg.get("metadata", "name") == "repo-maintenance"
