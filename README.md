# Repository maintenance

[![Spelling checked](https://img.shields.io/badge/cspell-checked-brightgreen.svg)](https://github.com/streetsidesoftware/cspell/tree/master/packages/cspell)

This repository is to standardize the developer environment of Python packages
by the [ComPWA organization](https://github.com/ComPWA). The maintenance is
performed through [pre-commit](https://pre-commit.com).

See also the [develop](https://pwa.readthedocs.io/develop.html) page on the
[PWA pages](https://pwa.readthedocs.io).

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
```

then run `pre-commit autoupdate`. This example lists all available hooks
(listed here as `id`s) ― you can remove some of them.
