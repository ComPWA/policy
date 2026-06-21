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

`uvx` caches the Git checkout, so add `--refresh` directly after `uvx` to pull the latest commit from the default branch.

If you run the command often, you can install it as a persistent tool with [`uv tool install`](https://docs.astral.sh/uv/concepts/tools) (or `pipx install`) and call `policy` directly, updating it with `uv tool upgrade --reinstall compwa-policy`. When the `pwa` command is installed alongside this package, the same command is also available as `pwa policy ...` through a `pwa.commands` entry point.

## Hook arguments

The `check-dev-files` hook (and the `policy` command without a subcommand) only accepts the options that are shared across the whole repository, such as `--repo-name`. These can be added to the [`args`](https://pre-commit.com/#config-args) key in your `.pre-commit-config.yaml` file. Options scoped to a single area (e.g. `--no-pypi`) are exposed on the matching subcommand instead and are configured through its `[tool.compwa.policy.<group>]` table (see [below](#configuration)). The full command tree and its options are:

```{typer} compwa_policy.cli:app
:prog: policy
:width: 80
:show-nested:
```

<!-- prettier-ignore-start -->
(configuration)=
## Configuration in `pyproject.toml`
<!-- prettier-ignore-end -->

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

:::{important}
After upgrading, the `check-dev-files` pre-commit hook **fails** if your `.pre-commit-config.yaml` still passes area-scoped flags (such as `--no-pypi` or `--no-binder`) under `args:`, because the hook now only accepts repository-wide options. Run the one-off `policy migrate` command below to fix this; you do **not** need to install anything first:

```shell
uvx --from git+https://github.com/ComPWA/policy policy migrate
```

:::

The `policy migrate` subcommand does this conversion automatically: it reads the `args:` of the `check-dev-files` hook in your `.pre-commit-config.yaml`, writes them into the hierarchical `[tool.compwa.policy]` table of `pyproject.toml`, and removes the now-redundant `args:` from the hook. To preview the resulting table without changing any files, add `--dry-run`:

```shell
uvx --from git+https://github.com/ComPWA/policy policy migrate --dry-run
```

If you already installed the `policy` command, you can drop the `uvx --from git+https://github.com/ComPWA/policy` prefix and simply run `policy migrate`.

The same command also relocates any notebook formatting hooks (such as `set-nb-cells` or `fix-nbformat-version`) that are still listed under the `ComPWA/policy` repo to a separate [`ComPWA/nbhooks`](https://github.com/ComPWA/nbhooks) repo entry, since those hooks were [extracted into their own repository](https://github.com/ComPWA/policy/issues/612).
