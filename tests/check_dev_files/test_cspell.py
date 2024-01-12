from pathlib import Path

import pytest
import yaml

from compwa_policy.check_dev_files.cspell import _update_cspell_repo_url
from compwa_policy.errors import PrecommitError
from compwa_policy.utilities.precommit import PrecommitConfig, fromdict


@pytest.fixture(scope="session")
def test_config_dir(test_dir: Path) -> Path:
    return test_dir / "check_dev_files/cspell"


@pytest.fixture(scope="session")
def good_config(test_config_dir: Path) -> PrecommitConfig:
    with open(test_config_dir / ".pre-commit-config-good.yaml") as stream:
        definition = yaml.safe_load(stream)
    return fromdict(definition, PrecommitConfig)


@pytest.mark.parametrize(
    ("test_config", "error"),
    [
        (".pre-commit-config-bad.yaml", True),
        (".pre-commit-config-good.yaml", False),
    ],
)
def test_update_cspell_repo_url(
    test_config: str,
    error,
    test_config_dir: Path,
    tmp_path: Path,
    good_config: PrecommitConfig,
):
    with open(test_config_dir / test_config) as stream:
        config_content = stream.read()
    config_path = tmp_path / test_config
    config_path.write_text(config_content)

    if error:
        with pytest.raises(
            PrecommitError, match=r"^Updated cSpell pre-commit repo URL"
        ):
            _update_cspell_repo_url(config_path)
    else:
        _update_cspell_repo_url(config_path)

    with open(config_path) as stream:
        definition = yaml.safe_load(stream)
    updated_config = fromdict(definition, PrecommitConfig)

    assert updated_config.repos[0].repo == good_config.repos[0].repo
