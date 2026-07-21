# ComPWA repository policy

:::{title} Welcome
:::

This repository standardizes and synchronizes the developer environment of [ComPWA repositories](https://github.com/orgs/ComPWA/repositories). Its [`check-dev-files`](./check-dev-files.md) hook keeps configuration files up to date as developer tools introduce new features and deprecate old ones. The policies are enforced through [pre-commit](https://pre-commit.com); all available hooks are listed in [`.pre-commit-hooks.yaml`](https://github.com/ComPWA/policy/blob/main/.pre-commit-hooks.yaml).

## Set up a repository

Add a [`.pre-commit-config.yaml`](https://pre-commit.com/index.html#adding-pre-commit-plugins-to-your-project) file to your repository and list which hooks you want to use:

```yaml
repos:
  - repo: https://github.com/ComPWA/policy
    rev: ""
    hooks:
      - id: check-dev-files
        args:
          - --repo-name="short name for your repository"
```

Then install and activate [`pre-commit`](https://pre-commit.com/#install):

```shell
pip install pre-commit
pre-commit autoupdate --repo=https://github.com/ComPWA/policy
pre-commit install
```

Running the hook for the first time turns this minimal configuration into the standard ComPWA developer setup:

```shell
pre-commit run check-dev-files --all-files
```

For an existing repository, `policy bootstrap` can detect its current setup and configure the hook automatically. See the {doc}`command-line guide <check-dev-files>` for bootstrapping, individual checks, and installation options.

The notebook formatting hooks that used to be served from this repository now live in [ComPWA/nbhooks](https://github.com/ComPWA/nbhooks).

```{toctree}
:hidden:
Command-line interface <check-dev-files>
API <api/compwa_policy>
Continuous benchmarks <https://compwa.github.io/policy-benchmark-results>
Changelog <https://github.com/ComPWA/policy/releases>
Upcoming features <https://github.com/ComPWA/policy/milestones?direction=asc&sort=title&state=open>
Help developing <https://compwa.github.io/develop>
```
