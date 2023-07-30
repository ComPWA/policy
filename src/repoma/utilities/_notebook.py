import os.path


def get_pip_target_dir(notebook_path: str) -> str:
    # cspell:ignore ipynb
    notebook_name = os.path.basename(notebook_path).replace(".ipynb", "")
    return f".pip/{notebook_name}"
