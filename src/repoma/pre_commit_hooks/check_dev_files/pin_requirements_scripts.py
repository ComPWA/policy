"""Check if there is a ``pin_requirements.py`` script."""

import os

from repoma.pre_commit_hooks.errors import PrecommitError

__CONSTRAINTS_DIR = ".constraints"
__SCRIPT_NAME = "pin_requirements.py"
__THIS_MODULE_DIR = os.path.abspath(os.path.dirname(__file__))
__EXPECTED_SCRIPT_PATH = os.path.abspath(
    f"{__THIS_MODULE_DIR}/../../devtools/{__SCRIPT_NAME}"
)
with open(__EXPECTED_SCRIPT_PATH) as STREAM:
    __EXPECTED_SCRIPT = STREAM.read()


def check_constraints_folder() -> None:
    update_pin_requirements_script()
    remove_bash_script()


def update_pin_requirements_script() -> None:
    if not os.path.exists(f"{__CONSTRAINTS_DIR}/{__SCRIPT_NAME}"):
        write_script()
        raise PrecommitError(
            f'This repository does not contain a "{__SCRIPT_NAME}" script.'
            " Problem has been fixed"
        )
    with open(f"{__CONSTRAINTS_DIR}/{__SCRIPT_NAME}") as stream:
        existing_script = stream.read()
    if existing_script != __EXPECTED_SCRIPT:
        write_script()
        raise PrecommitError(f'Updated "{__SCRIPT_NAME}" script')


def remove_bash_script() -> None:
    bash_script_name = f"{__CONSTRAINTS_DIR}/upgrade.sh"
    if os.path.exists(bash_script_name):
        os.remove(bash_script_name)
        raise PrecommitError(f'Removed deprecated "{bash_script_name}" script')


def write_script() -> None:
    with open(f"{__CONSTRAINTS_DIR}/{__SCRIPT_NAME}", "w") as stream:
        stream.write(__EXPECTED_SCRIPT)
