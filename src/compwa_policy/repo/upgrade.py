"""Generate dependency upgrade commands for supported project types."""

from __future__ import annotations

from compwa_policy.utilities.match import git_ls_files

UV_UPGRADE_IMPORTS = ["pathlib", "subprocess"]
UV_UPGRADE_EXPRESSION = """
all(
    subprocess.run(
        ["uv", "lock", "--upgrade", "--directory", str(pathlib.Path(file).parent)],
        check=False,
    ).returncode == 0
    for file in subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if pathlib.Path(file).name == "pyproject.toml"
)
"""


def has_nested_uv_lock() -> bool:
    return any(path != "uv.lock" for path in git_ls_files("uv.lock", "**/uv.lock"))


def get_uv_upgrade_script() -> str:
    imports = "\n".join(f"import {module}" for module in UV_UPGRADE_IMPORTS)
    return f"{imports}\n\nraise SystemExit(not {UV_UPGRADE_EXPRESSION.strip()})"


def get_julia_manifest_paths() -> list[str]:
    return git_ls_files("Manifest.toml", "**/Manifest.toml")


def get_julia_upgrade_command(manifest_paths: list[str]) -> str:
    if len(manifest_paths) == 1:
        project = manifest_paths[0].rpartition("/")[0] or "."
        return f"julia --eval='using Pkg; Pkg.update()' --project={project}"
    return """
julia --eval='
using Pkg

files = readlines(`git ls-files`)
projects = (dirname(file) for file in files if basename(file) == "Manifest.toml")
failed = [
    project
    for project in projects
    if try
        Pkg.activate(project)
        Pkg.update()
        false
    catch
        true
    end
]
exit(!isempty(failed))
'
"""
