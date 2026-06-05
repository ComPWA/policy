# `check-dev-files`

This hook is responsible for standardizing and synchronizing the [developer environment](https://compwa.github.io/develop) of repositories by the [ComPWA organization](https://github.com/ComPWA). Coding conventions are enforced through automated checks instead of through a contribution guide. These conventions have to be regularly updated across all repositories as developer tools introduce new features and deprecate old ones.

The `check-dev-files` hook can also be used as a **cookie cutter** for new repositories by adding the following to your [`.pre-commit-config.yaml`](https://pre-commit.com/index.html#adding-pre-commit-plugins-to-your-project) file:

```yaml
repos:
  - repo: https://github.com/ComPWA/policy
    rev: ""
    hooks:
      - id: check-dev-files
        args:
          - --repo-name="short name for your repository"
```

and running

```shell
pre-commit autoupdate --repo=https://github.com/ComPWA/policy
pre-commit run check-dev-files -a
```

For more implementation details of this hook, check the {mod}`.check_dev_files` module.

## Command-line interface

The checks are also exposed through a short [Typer](https://typer.tiangolo.com)-based `policy` command. Running `policy` without a subcommand runs every check at once, which is exactly what the `check-dev-files` pre-commit hook does. The subcommands group the checks by domain, so you can run just a subset. To see which subcommands are available, run:

```shell
policy --help
```

When the `pwa` command is installed alongside this package, the same command is also available as `pwa policy ...` through a `pwa.commands` entry point.

## Hook arguments

The `check-dev-files` hook (and the `policy` command without a subcommand) can be configured by adding any of the following flags to the [`args`](https://pre-commit.com/#config-args) key in your `.pre-commit-config.yaml` file.

```{typer} compwa_policy.check_dev_files.cli:app
:prog: policy
:width: 80
:show-nested:
```
