# How to contribute?

[![Open in Visual Studio Code](https://img.shields.io/badge/vscode-open-blue?logo=visualstudiocode)](https://open.vscode.dev/ComPWA/policy)

> [!TIP]
> This package is part of the [ComPWA Organization](https://github.com/ComPWA). For more information about how to contribute to the packages, go to **[compwa.github.io/develop](https://compwa.github.io/develop)**!

To contribute to the project, you need to install the package in a virtual environment. This can be done best with [`uv`](https://docs.astral.sh/uv) (see installation instructions [here](https://docs.astral.sh/uv/getting-started/installation)). For this, you first need to get the source code with [Git](https://git-scm.com):

```shell
git clone https://github.com/ComPWA/policy
cd policy
```

Now it's simply a matter of creating and activating the [virtual environment](https://docs.astral.sh/uv/pip/environments) with [`uv sync`](https://docs.astral.sh/uv/reference/cli/#uv-sync). The dependencies for the project are 'pinned' in each commit through the [`uv.lock` file](https://docs.astral.sh/uv/concepts/projects/#project-lockfile).

```shell
uv sync
source .venv/bin/activate
```