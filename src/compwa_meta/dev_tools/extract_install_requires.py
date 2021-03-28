# cspell:ignore nargs
"""Extract :code:`install_requires` section to :file:`requirements.in`."""

import argparse
import configparser
from os.path import exists
from typing import Optional, Sequence


def extract_install_requires(directory: str) -> None:
    if not exists(f"{directory}/setup.cfg"):
        raise FileNotFoundError(
            f'Directory "{directory}" does not contain a setup.cfg file'
        )
    cfg = configparser.ConfigParser()
    cfg.read(f"{directory}/setup.cfg")
    install_requires = cfg.get("options", "install_requires", raw=False)
    install_requires = install_requires[1:]  # remove first line (empty)
    with open(f"{directory}/reqs/requirements.in", "w") as stream:
        stream.write(install_requires)

    if "options.extras_require" in cfg:
        extras_require = "\n".join(
            cfg.get("options.extras_require", str(section), raw=False)
            for section in cfg["options.extras_require"]
        )
        extras_require = f"-r requirements.in\n{extras_require}"
        extras_require = extras_require.replace("\n\n", "\n")
        with open(f"{directory}/reqs/requirements-extras.in", "w") as stream:
            stream.write(extras_require)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(argument_default=".")
    parser.add_argument(
        "directory",
        type=str,
        default=".",
        nargs="?",
        help="Directory containing a setup.cfg file from which the "
        "requirements should be extracted.",
    )
    args = parser.parse_args(argv)
    extract_install_requires(args.directory)
    return 0


if __name__ == "__main__":
    main()
