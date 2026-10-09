# Command-line interface

The `check-dev-files` checks are also exposed through a short [Typer](https://typer.tiangolo.com)-based `policy` command. Running `policy` without a subcommand runs every check at once, exactly like the `check-dev-files` pre-commit hook. The subcommands group the checks by domain, so you can run just a subset.

You do not need to install anything: with [`uv`](https://docs.astral.sh/uv), `uvx` fetches and runs the command on the fly. For example, to see which subcommands are available:

```shell
uvx --from git+https://github.com/ComPWA/policy policy --help
```

:::{tip}
`uvx` caches the Git checkout, so add `--refresh` directly after `uvx` to pull the latest commit from the default branch.
:::

If you run the command often, you can install it as a persistent tool with [`uv tool install`](https://docs.astral.sh/uv/concepts/tools) (or `pipx install`) and call `policy` directly, updating it with `uv tool upgrade --reinstall compwa-policy`. When the `pwa` command is installed alongside this package, the same command is also available as `pwa policy ...` through a `pwa.commands` entry point.

## Hook arguments

The `check-dev-files` hook (and the `policy` command without a subcommand) only accepts the options that are shared across the whole repository, such as `--repo-name`. These can be added to the [`args`](https://pre-commit.com/#config-args) key in your `.pre-commit-config.yaml` file. Options scoped to a single area (for example, `--no-pypi`) are exposed on the matching subcommand and are configured through its `[tool.compwa.policy.<group>]` table. See {doc}`check-dev-files/configuration` for details.

The full command tree and its options are:

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

```{toctree}
:hidden:
Configuration <check-dev-files/configuration>
Migrations <check-dev-files/migrations>
```
