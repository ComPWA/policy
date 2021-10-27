# Repository maintenance

[![BSD 3-Clause license](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Spelling checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell)
[![GitPod](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/ComPWA/repo-maintenance)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ComPWA/repo-maintenance/main.svg)](https://results.pre-commit.ci/latest/github/ComPWA/repo-maintenance/main)
[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)

This repository is to standardize the developer environment of Python packages
by the [ComPWA organization](https://github.com/ComPWA). The maintenance is
performed through [pre-commit](https://pre-commit.com).

See also the
[develop](https://compwa-org.readthedocs.io/en/stable/develop.html) page.

## Usage

Add a `.pre-commit-config.yaml` file to your repository with the following
content:

```yaml
repos:
  - repo: https://github.com/ComPWA/repo-maintenance
    rev: ""
    hooks:
      - id: check-dev-files
      - id: fix-first-nbcell
      - id: fix-nbformat-version
      - id: format-setup-cfg
      - id: pin-nb-requirements
```

then run `pre-commit autoupdate`. This example lists all available hooks
(listed here as `id`s) ― you can remove some of them.
