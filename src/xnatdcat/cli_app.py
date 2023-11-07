import argparse
import logging
from pathlib import Path, PurePath
from typing import Dict

# Python < 3.11 does not have tomllib, but tomli provides same functionality
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import xnat

from .__about__ import __version__
from .xnat_parser import xnat_to_RDF

# The location of this file (cli_app.py) is known, this leads to project root folder
EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'example-config.toml'

logger = logging.getLogger(__name__)


def __parse_cli_args():
    """Simple argument parser for commandline args"""

    parser = argparse.ArgumentParser(prog="xnatdcat", description="This tool generates DCAT from XNAT")
    parser.add_argument(
        "server",
        type=str,
        help="URI of the server to connect to (including http:// or https://)",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=None,
        type=str,
        help="Username to use, leave empty to use netrc entry or anonymous login.",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=None,
        type=str,
        help=(
            "Password to use with the username, leave empty when using netrc. If a"
            " username is given and no password, there will be a prompt on the console"
            " requesting the password."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        type=PurePath,
        help="Destination file to write output to. If not set, the script will print serialized output to stdout.",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="turtle",
        type=str,
        help=(
            "The format that the output should be written in. This value references a"
            " Serializer plugin in RDFlib. Supportd values are: "
            " \"xml\", \"n3\", \"turtle\", \"nt\", \"pretty-xml\", \"trix\", \"trig\", \"nquads\","
            " \"json-ld\" and \"hext\". Defaults to \"turtle\"."
        ),
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        type=Path,
        help="Configuration file to use. If not set, will use ~/.xnatdcat/config.toml if it exists.",
    )

    parser.add_argument(
        "-pr",
        "--project",
        default=False,
        type=str,
        help="Specify if only a specific project is selected.",
    )

    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    return args


def __connect_xnat(args):
    """Very simple function to connect to XNat and get a session"""
    session = xnat.connect(server=args.server, user=args.username, password=args.password)

    return session


def load_configuration(config_path: Path = None) -> Dict:
    """Loads a configuration file for XNATDCAT

    First, it checks if config_path is given. If not, it will look for ~/.xnatdcat/config.toml,
    if that file also doesn't exist it will load an example configuration from the project rootfolder.

    Parameters
    ----------
    config_path : Path, optional
        Path to configuration file to load, by default None

    Returns
    -------
    Dict
        Dictionary with loaded configuration properties

    Raises
    ------
    FileNotFoundError
        If config_path is specified yet does not exist
    """
    if config_path:
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file does not exist at {config_path}")
    elif (config_path := Path.home() / ".xnatdcat" / "config.toml").exists():
        pass
    else:
        # Python 3.8 does not support slicing of paths yet :(
        config_path = EXAMPLE_CONFIG_PATH
        logger.warning("No configuration file found or specified! xnatdcat will use the example file.")

    logger.info("Using configuration file %s", config_path)

    with open(config_path, 'rb') as f:
        config = tomllib.load(f)

    return config


def cli_main():
    args = __parse_cli_args()

    session = __connect_xnat(args)
    config = load_configuration(args.config)
    project = args.project

    if project:
        try:
            projects = [session.projects[project]]
        except KeyError as e:
            logger.warning(f"Project can not be find in XNAT: {e}")
            exit()
    g = xnat_to_RDF(session, config, project)

    if args.output:
        g.serialize(destination=args.output, format=args.format)
    else:
        print(g.serialize(format=args.format))


if __name__ == "__main__":
    cli_main()
