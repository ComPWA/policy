# ComPWA repo maintenance!

:::{title} Welcome
:::

This package standardizes and synchronizes the developer environment of repositories by the [ComPWA organization](https://github.com/ComPWA). The maintenance is performed through [pre-commit](https://pre-commit.com) with the use of a number of pre-commit hooks as defined by [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml). The {mod}`check-dev-files <.check_dev_files>` in particular can be used as a **cookie cutter** for new repositories.

## Usage

Add a [`.pre-commit-config.yaml`](https://pre-commit.com/index.html#adding-pre-commit-plugins-to-your-project) file to your repository and list which hooks you want to use:

```yaml
repos:
  - repo: https://github.com/ComPWA/repo-maintenance
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
pre-commit autoupdate --repo=https://github.com/ComPWA/repo-maintenance
pre-commit install
```

The `repo-maintenance` repository provides the following hooks:

- {mod}`check-dev-files <.check_dev_files>`
- {mod}`colab-toc-visible <.colab_toc_visible>`
- {mod}`fix-nbformat-version <.fix_nbformat_version>`
- {mod}`format-setup-cfg <.format_setup_cfg>`
- {mod}`pin-nb-requirements <.pin_nb_requirements>`
- {mod}`set-nb-cells <.set_nb_cells>`

```{toctree}
:hidden:
API <api/repoma>
Changelog <https://github.com/ComPWA/repoma/releases>
Upcoming features <https://github.com/ComPWA/repoma/milestones?direction=asc&sort=title&state=open>
Help developing <https://compwa-org.rtfd.io/en/stable/develop.html>
```
