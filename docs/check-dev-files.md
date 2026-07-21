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

For more implementation details of this hook, check the {mod}`compwa_policy.cli` module.

## Command-line interface

The checks are also exposed through a short [Typer](https://typer.tiangolo.com)-based `policy` command. Running `policy` without a subcommand runs every check at once, which is exactly what the `check-dev-files` pre-commit hook does. The subcommands group the checks by domain, so you can run just a subset.

You do not need to install anything: with [`uv`](https://docs.astral.sh/uv), `uvx` fetches and runs the command on the fly. For example, to see which subcommands are available:

```shell
uvx --from git+https://github.com/ComPWA/policy policy --help
```

:::{tip}
`uvx` caches the Git checkout, so add `--refresh` directly after `uvx` to pull the latest commit from the default branch.
:::

If you run the command often, you can install it as a persistent tool with [`uv tool install`](https://docs.astral.sh/uv/concepts/tools) (or `pipx install`) and call `policy` directly, updating it with `uv tool upgrade --reinstall compwa-policy`. When the `pwa` command is installed alongside this package, the same command is also available as `pwa policy ...` through a `pwa.commands` entry point.

## Hook arguments

The `check-dev-files` hook (and the `policy` command without a subcommand) only accepts the options that are shared across the whole repository, such as `--repo-name`. These can be added to the [`args`](https://pre-commit.com/#config-args) key in your `.pre-commit-config.yaml` file. Options scoped to a single area (e.g. `--no-pypi`) are exposed on the matching subcommand instead and are configured through its `[tool.compwa.policy.<group>]` table (see [below](#configuration)). The full command tree and its options are:

```{typer} compwa_policy.cli:app
:prog: policy
:width: 80
:show-nested:
```

## Bootstrapping an existing repository

Run `policy bootstrap` in an existing repository to detect whether it contains Python code, which package manager it uses, and which type checkers are already configured. The command records those choices in `pyproject.toml` under `[tool.compwa.policy]` and adds the `check-dev-files` hook to `.pre-commit-config.yaml`, preserving existing configuration in both files.

```shell
uvx --from git+https://github.com/ComPWA/policy policy bootstrap
```

<!-- prettier-ignore-start -->
(configuration)=
## Configuration in `pyproject.toml`
<!-- prettier-ignore-end -->

Instead of repeating the same flags under `args:` in every `.pre-commit-config.yaml`, a repository can declare its options once in a `[tool.compwa.policy]` table in its `pyproject.toml`. Each option is resolved with the following precedence (first match wins):

1. the option explicitly passed on the command line (e.g. under `args:`);
2. the `[tool.compwa.policy]` table in `pyproject.toml`;
3. the built-in default.

The table mirrors the subcommand tree. Shared options live at the top level, while
subcommand-specific options live in nested tables. The following copyable example is
generated from the settings schema and shows every built-in default:

```{eval-rst}
.. policy-settings::
    :caption: pyproject.toml
```

The `env` subcommand maps to the `setup` table. Environment variables can be added as
key-value pairs under `[tool.compwa.policy.setup.env]`.

Both the native TOML form (arrays, tables, booleans) and the legacy command-line string form (`"mypy,pyright"`, `"A=1,B=2"`) are accepted, so an existing `args:` list can be moved into `pyproject.toml` verbatim.

## Migrating after breaking changes

Some policy updates introduce breaking changes to a repository's configuration. The `check-dev-files` pre-commit hook cannot rewrite your files to apply such a change itself — it can only detect it and fail. The `policy migrate` command applies these migrations for you, but because it modifies configuration files it has to be run **outside of `pre-commit`**, as a one-off command.

:::{important}
If the `check-dev-files` hook starts failing after an upgrade, run `policy migrate` to bring your configuration up to date. You do **not** need to install anything first:

```shell
uvx --from git+https://github.com/ComPWA/policy --refresh policy migrate
```

:::

To preview the changes without writing any files, add `--dry-run`:

```shell
uvx --from git+https://github.com/ComPWA/policy --refresh policy migrate --dry-run
```

If you already installed the `policy` command, you can drop the `uvx --from git+https://github.com/ComPWA/policy` prefix and simply run `policy migrate`.
