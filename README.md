# ComPWA repository policy

[![BSD 3-Clause license](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Spelling checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/main/packages/cspell)
[![CI](https://github.com/ComPWA/policy/actions/workflows/ci.yml/badge.svg)](https://github.com/ComPWA/policy/actions/workflows/ci.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ComPWA/policy/main.svg)](https://results.pre-commit.ci/latest/github/ComPWA/policy/main)
[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

This repository sets the policies for developer environment in repositories if the [ComPWA organization](https://github.com/ComPWA) (See our [Help developing](https://compwa.github.io/develop) page). The policies are automatically enforced through [pre-commit](https://pre-commit.com).

## Usage

Add a `.pre-commit-config.yaml` file to your repository with the following content:

```yaml
repos:
  - repo: https://github.com/ComPWA/policy
    rev: ""
    hooks:
      - id: check-dev-files
```

then run

```shell
pre-commit autoupdate --repo=https://github.com/ComPWA/policy
```

The notebook formatting hooks that used to live here have moved to [ComPWA/nbhooks](https://github.com/ComPWA/nbhooks). When a repository contains notebooks, `check-dev-files` automatically migrates them over and keeps them up to date.

## Command-line interface

The same checks are exposed through a short [Typer](https://typer.tiangolo.com)-based `policy` command, so you can run them on the fly without setting up `pre-commit` first:

```shell
uvx --from git+https://github.com/ComPWA/policy policy --help
```

Running `policy` without a subcommand runs every check at once, exactly like the `check-dev-files` hook. Subcommands group the checks by domain, so you can run just a subset (e.g. `policy python` or `policy nb`). Options that apply to the whole repository can be declared once in a `[tool.compwa.policy]` table in your `pyproject.toml` instead of repeating them under `args:`. See the [`check-dev-files` documentation](https://compwa.github.io/policy/check-dev-files) for the full command tree and configuration options.
