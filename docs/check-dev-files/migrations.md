# Migrating after breaking changes

Some policy updates introduce breaking changes to a repository's configuration.
The `check-dev-files` pre-commit hook cannot rewrite your files to apply such a
change itself—it can only detect it and fail. The `policy migrate` command applies
these migrations for you, but because it modifies configuration files it has to be
run **outside of pre-commit**, as a one-off command.

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
