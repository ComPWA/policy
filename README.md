# ComPWA repository policy

[![BSD 3-Clause license](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Spelling checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell)
[![CI](https://github.com/ComPWA/policy/actions/workflows/ci.yml/badge.svg)](https://github.com/ComPWA/policy/actions/workflows/ci.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ComPWA/policy/main.svg)](https://results.pre-commit.ci/latest/github/ComPWA/policy/main)
[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This repository sets the policies for developer environment in repositories if the [ComPWA organization](https://github.com/ComPWA) (See our [Help developing](https://compwa.github.io/develop) page). The policies are automatically enforced through [pre-commit](https://pre-commit.com).

## Usage

Add a `.pre-commit-config.yaml` file to your repository with the following content:

```yaml
repos:
  - repo: https://github.com/ComPWA/policy
    rev: ""
    hooks:
      - id: check-dev-files
      - id: fix-nbformat-version
      - id: set-nb-cells
```

then run

```shell
pre-commit autoupdate --repo=https://github.com/ComPWA/policy
```

This example lists [all available hooks](./.pre-commit-hooks.yaml) (listed here as `id`s) ― you can remove some of them.
