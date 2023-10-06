# `check-dev-files`

This hook is responsible for standardizing and synchronizing the [developer environment](https://compwa-org.rtfd.io/develop.html) of repositories by the [ComPWA organization](https://github.com/ComPWA). Coding conventions are enforced through automated checks instead of through a contribution guide. These conventions have to be regularly updated across all repositories as developer tools introduce new features and deprecate old ones.

The `check-dev-files` hook can also be used as a **cookie cutter** for new repositories by adding the following to your [`.pre-commit-config.yaml`](https://pre-commit.com/index.html#adding-pre-commit-plugins-to-your-project) file:

```yaml
repos:
  - repo: https://github.com/ComPWA/repo-maintenance
    rev: ""
    hooks:
      - id: check-dev-files
        args:
          - --repo-name="short name for your repository"
```

and running

```shell
pre-commit autoupdate --repo=https://github.com/ComPWA/repo-maintenance
pre-commit run check-dev-files -a
```

For more implementation details of this hook, check the {mod}`.check_dev_files` module.

## Hook arguments

The `check-dev-files` hook can be configured with by adding any of the following flags to the [`args`](https://pre-commit.com/#config-args) key in your `.pre-commit-config.yaml` file.

```{argparse}
:module: repoma.check_dev_files
:func: _create_argparse
:prog: check-dev-files
```
