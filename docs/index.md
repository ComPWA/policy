# ComPWA repository policy

:::{title} Welcome
:::

This repository sets policies for [repositories of the ComPWA organization](https://github.com/orgs/ComPWA/repositories). The policies are enforced through [pre-commit](https://pre-commit.com) with the use of a number of pre-commit hooks as defined by [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml). The [`check-dev-files`](./check-dev-files.md) in particular can be used as a **cookie cutter** for new repositories.

## Usage

Add a [`.pre-commit-config.yaml`](https://pre-commit.com/index.html#adding-pre-commit-plugins-to-your-project) file to your repository and list which hooks you want to use:

```yaml
repos:
  - repo: https://github.com/ComPWA/policy
    rev: ""
    hooks:
      - id: check-dev-files
        args:
          - --repo-name="short name for your repository"
      - id: colab-toc-visible
      - id: fix-nbformat-version
      - id: format-setup-cfg
      - id: pin-nb-requirements
      - id: set-nb-cells
```

and install and activate [`pre-commit`](https://pre-commit.com/#install) as follows:

```shell
pip install pre-commit
pre-commit autoupdate --repo=https://github.com/ComPWA/policy
pre-commit install
```

The **ComPWA/policy** repository provides the following hooks:

- [`check-dev-files`](./check-dev-files.md)
- {mod}`colab-toc-visible <.colab_toc_visible>`
- {mod}`fix-nbformat-version <.fix_nbformat_version>`
- {mod}`format-setup-cfg <.format_setup_cfg>`
- {mod}`pin-nb-requirements <.pin_nb_requirements>`
- {mod}`set-nb-cells <.set_nb_cells>`

```{toctree}
:hidden:
check-dev-files
API <api/compwa_policy>
Changelog <https://github.com/ComPWA/policy/releases>
Upcoming features <https://github.com/ComPWA/policy/milestones?direction=asc&sort=title&state=open>
Help developing <https://compwa-org.rtfd.io/develop.html>
```
