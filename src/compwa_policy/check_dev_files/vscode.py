"""Check configuration of VS Code."""

import os

from compwa_policy.check_dev_files.conda import PackageManagerChoice
from compwa_policy.utilities import CONFIG_PATH, vscode
from compwa_policy.utilities.executor import Executor
from compwa_policy.utilities.python import has_constraint_files


def main(
    has_notebooks: bool, is_python_repo: bool, package_manager: PackageManagerChoice
) -> None:
    with Executor() as do:
        do(_update_extensions)
        do(_update_settings, has_notebooks, is_python_repo, package_manager)


def _update_extensions() -> None:
    with Executor() as do:
        do(
            vscode.add_extension_recommendation,
            "eamodio.gitlens",  # cspell:ignore eamodio
        )
        do(
            vscode.add_extension_recommendation,
            "mhutchie.git-graph",  # cspell:ignore mhutchie
        )
        do(
            vscode.add_extension_recommendation,
            "soulcode.vscode-unwanted-extensions",  # cspell:ignore Soulcode
        )
        do(
            vscode.add_extension_recommendation,
            "stkb.rewrap",  # cspell:ignore stkb
        )
        do(
            vscode.remove_extension_recommendation,
            "garaioag.garaio-vscode-unwanted-recommendations",  # cspell:ignore garaio garaioag
            unwanted=True,
        )
        do(
            vscode.remove_extension_recommendation,
            "travisillig.vscode-json-stable-stringify",  # cspell:ignore travisillig
            unwanted=True,
        )
        do(
            vscode.remove_extension_recommendation,
            "tyriar.sort-lines",  # cspell:ignore tyriar
            unwanted=True,
        )


def _update_settings(
    has_notebooks: bool, is_python_repo: bool, package_manager: PackageManagerChoice
) -> None:
    with Executor() as do:
        do(
            vscode.update_settings,
            {
                "diffEditor.experimental.showMoves": True,
                "editor.formatOnSave": True,
                "gitlens.telemetry.enabled": False,
                "multiDiffEditor.experimental.enabled": True,
                "redhat.telemetry.enabled": False,
                "telemetry.telemetryLevel": "off",
            },
        )
        do(
            vscode.update_settings,
            {
                "[git-commit]": {
                    "editor.rulers": [72],
                    "rewrap.wrappingColumn": 72,
                },
                "[json]": {
                    "editor.wordWrap": "on",
                },
            },
        )
        do(_remove_outdated_settings)
        do(_update_doc_settings)
        if has_notebooks:
            do(_update_notebook_settings)
        do(_update_pytest_settings)
        if has_constraint_files():
            do(
                vscode.update_settings,
                {"files.associations": {"**/.constraints/py*.txt": "pip-requirements"}},
            )
        if is_python_repo:
            if package_manager == "pixi":
                python_path = ".pixi/envs/default/bin/python"
            else:
                python_path = ".venv/bin/python"
            do(
                vscode.update_settings,
                {
                    "python.defaultInterpreterPath": python_path,
                    "rewrap.wrappingColumn": 88,
                },
            )
            if CONFIG_PATH.envrc.exists():
                do(
                    vscode.update_settings,
                    {"python.terminal.activateEnvironment": False},
                )


def _remove_outdated_settings() -> None:
    outdated_settings = [
        "editor.rulers",
        "githubPullRequests.telemetry.enabled",
        "gitlens.advanced.telemetry.enabled",
        "python.analysis.diagnosticMode",
        "python.analysis.typeCheckingMode",
        "python.formatting.provider",
        "python.linting.banditEnabled",
        "python.linting.enabled",
        "python.linting.flake8Enabled",
        "python.linting.mypyEnabled",
        "python.linting.pydocstyleEnabled",
        "python.linting.pylamaEnabled",
        "python.linting.pylintEnabled",
        "telemetry.enableCrashReporter",
        "telemetry.enableTelemetry",
    ]
    vscode.remove_settings(outdated_settings)


def _update_doc_settings() -> None:
    if not os.path.exists("docs/"):
        return
    settings = {
        "livePreview.defaultPreviewPath": "docs/_build/html",
    }
    with Executor() as do:
        do(vscode.update_settings, settings)
        do(vscode.add_extension_recommendation, "ms-vscode.live-server")
        # cspell:ignore executablebookproject
        myst_extension = "executablebookproject.myst-highlight"
        unwanted_extensions = vscode.get_unwanted_extensions()
        if myst_extension not in unwanted_extensions:
            do(vscode.add_extension_recommendation, myst_extension)


def _update_notebook_settings() -> None:
    """https://code.visualstudio.com/updates/v1_83#_go-to-symbol-in-notebooks."""
    if not os.path.exists("docs/"):
        return
    settings = {
        "notebook.gotoSymbols.showAllSymbols": True,
    }
    vscode.update_settings(settings)


def _update_pytest_settings() -> None:
    if not os.path.exists("tests/"):
        return
    pytest_settings = {
        "python.analysis.inlayHints.pytestParameters": True,
        "python.testing.pytestEnabled": True,
        "python.testing.unittestEnabled": False,
    }
    vscode.update_settings(pytest_settings)
