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

## Configuration in `pyproject.toml`

Instead of repeating the same flags under `args:` in every `.pre-commit-config.yaml`, a repository can declare its options once in a `[tool.compwa.policy]` table in its `pyproject.toml`. Each option is resolved with the following precedence (first match wins):

1. the option explicitly passed on the command line (e.g. under `args:`);
2. the `[tool.compwa.policy]` table in `pyproject.toml`;
3. the built-in default.

The table is organized hierarchically, mirroring the subcommand tree: options shared by several checks live in the top-level table, while options that belong to a single subcommand live in a sub-table named after it. The `env` subcommand maps to a `setup` table, and environment variables are a plain nested table under `[tool.compwa.policy.setup.env]`:

```toml
[tool.compwa.policy]
# options shared by several checks
dev-python-version = "3.13"
package-manager = "pixi"

[tool.compwa.policy.python]
imports-on-top = true
type-checker = ["mypy", "pyright"]

[tool.compwa.policy.nb]
no-binder = true
allowed-cell-metadata = ["scrolled"]

# options of the `env` subcommand (uv, conda, pixi, direnv)
[tool.compwa.policy.setup]
keep-contributing-md = true

# environment variables, as a plain TOML table
[tool.compwa.policy.setup.env]
PYTHONHASHSEED = "0"

[tool.compwa.policy.repo]
gitpod = true
```

Both the native TOML form (arrays, tables, booleans) and the legacy command-line string form (`"mypy,pyright"`, `"A=1,B=2"`) are accepted, so an existing `args:` list can be moved into `pyproject.toml` verbatim.

### Migrating an existing `args:` list

The `policy migrate` subcommand does this conversion automatically. It reads the `args:` of the `check-dev-files` hook in your `.pre-commit-config.yaml`, writes them into the hierarchical `[tool.compwa.policy]` table of `pyproject.toml`, and removes the now-redundant `args:` from the hook:

```shell
policy migrate            # convert .pre-commit-config.yaml in the current directory
policy migrate --dry-run  # preview the resulting table without changing any files
```
