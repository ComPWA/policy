<!-- prettier-ignore-start -->
(configuration)=
# Configuration
<!-- prettier-ignore-end -->

Instead of repeating the same flags under `args:` in every
`.pre-commit-config.yaml`, a repository can declare its options once in a
`[tool.compwa.policy]` table in `pyproject.toml`. Each option is resolved with the
following precedence (first match wins):

1. the option explicitly passed on the command line (for example, under `args:`);
2. the `[tool.compwa.policy]` table in `pyproject.toml`;
3. the built-in default.

The table mirrors the {doc}`subcommand tree <../check-dev-files>`. Shared options
live at the top level, while subcommand-specific options live in nested tables. The
following copyable example is generated from the settings schema and shows every
built-in default. Hover over an option to see what it does:

```{eval-rst}
.. policy-settings::
    :caption: pyproject.toml
```

The `env` subcommand maps to the `setup` table. Environment variables can be added
as key-value pairs under `[tool.compwa.policy.setup.env]`.

Both the native TOML form (arrays, tables, booleans) and the legacy command-line
string form (`"mypy,pyright"`, `"A=1,B=2"`) are accepted, so an existing `args:` list
can be moved into `pyproject.toml` verbatim.
