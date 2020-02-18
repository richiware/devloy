# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

import argparse
import logging

from . import start, stop
from .defaults import Defaults

logger = None


def arg_parser(args):
    global logger

    # Before execute verb, load default values from configuration.
    defaults = Defaults()

    parser = argparse.ArgumentParser(
            prog='devloy',
            description='Command to deploy dockerized development environments.')
    parser.add_argument(
            '--debug',
            action='store_true',
            help='Print debug info.'
    )

    subparsers = parser.add_subparsers(help='verbs help')
    start.add_subparser(subparsers, defaults)
    stop.add_subparser(subparsers)

    verb = parser.parse_args(args)
    # Set log level
    if verb.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    verb.func(verb, defaults, logger)


def main(argv=None):
    """
    Starting point of the command

    Logic:

    * Get arguments and execute verb

    :param list argv: The list of arguments
    :returns: The return code
    """
    # Create a custom logger
    global logger
    logger = logging.getLogger(__name__)
    # - Create handlers
    c_handler = logging.StreamHandler()
    # - Create formatters and add it to handlers
    c_format = '[%(asctime)s][devloy][%(levelname)s] %(message)s'
    c_format = logging.Formatter(c_format)
    c_handler.setFormatter(c_format)
    # - Add handlers to the logger
    logger.addHandler(c_handler)

    arg_parser(argv)
