<!-- prettier-ignore-start -->
(configuration)=
# Configuration
<!-- prettier-ignore-end -->

Instead of repeating the same flags under `args:` in every `.pre-commit-config.yaml`, a repository can declare its options once in a {cfg}`.tool.compwa.policy` table in `pyproject.toml`. Each option is resolved with the following precedence (first match wins):

1. the option explicitly passed on the command line (for example, under `args:`);
2. the {cfg}`.tool.compwa.policy` table in `pyproject.toml`;
3. the built-in default.

The table mirrors the {doc}`subcommand tree <../check-dev-files>`. Shared options live at the top level, while subcommand-specific options live in nested tables. The following copyable example is generated from the settings schema and shows defaults and examples. Commented options are examples; leave them commented to retain their defaults. Hover over an option to see what it does:

```{eval-rst}
.. config-schema:: /../compwa-policy.schema.json
    :caption: pyproject.toml
    :table: tool.compwa.policy
    :header-titles:
```

Policy installs and configures a set of tools by default. To keep it from managing one of them, list it under `disable` in the top-level table, for example `disable = ["binder", "ruff"]`, or pass `--disable` on the command line. Some tools, such as Gitpod, are off by default; list them under `enable` to have policy manage them, for example `enable = ["gitpod"]`. Both lists take the same tool names, and `disable` wins when a tool appears in both.

The `env` subcommand maps to the {cfg}`.setup` table. Environment variables can be added as key-value pairs under {cfg}`.setup.env`.

Both the native TOML form (arrays, tables, booleans) and the legacy command-line string form (`"mypy,pyright"`, `"A=1,B=2"`) are accepted, so an existing `args:` list can be moved into `pyproject.toml` verbatim.
