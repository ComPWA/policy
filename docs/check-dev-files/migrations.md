# Migrating after breaking changes

Some policy updates introduce breaking changes to a repository's configuration.
The `check-dev-files` hook cannot rewrite your files to apply such a
change itself—it can only detect it and fail. The `policy migrate` command applies
these migrations for you, but because it modifies configuration files it has to be
run **outside of prek**, as a one-off command.

:::{important}
If the `check-dev-files` hook starts failing after an upgrade, run `policy migrate`
to bring your configuration up to date. You do **not** need to install anything
first:

```shell
uvx --from git+https://github.com/ComPWA/policy --refresh policy migrate
```

:::

To preview the changes without writing any files, add `--dry-run`:

```shell
uvx --from git+https://github.com/ComPWA/policy --refresh policy migrate --dry-run
```

If you already installed the `policy` command, you can drop the
`uvx --from git+https://github.com/ComPWA/policy` prefix and simply run
`policy migrate`.

## From `pre-commit` to `prek`

ComPWA repositories now run their hooks with [prek](https://prek.j178.dev) instead of
[pre-commit](https://pre-commit.com). `prek` is a drop-in replacement that reads the
same `.pre-commit-config.yaml` file, so the hook definitions themselves do not change.
The `check-dev-files` hook updates the parts that live in tracked files (the
`CONTRIBUTING.md` instructions, the `_upgrade-prek` task, and the removal of
`pre-commit` from the dependency groups), but it cannot touch the Git hook shims under
`.git/hooks`, because those are installed locally by each developer.

Running `policy migrate` detects shims that were written by `pre-commit install` and
replaces them with `prek` shims:

```shell
uv tool install prek
uvx --from git+https://github.com/ComPWA/policy --refresh policy migrate
```

If `prek` is not on your `PATH`, the existing shims are left in place and the command
to run after installing `prek` is printed instead.
