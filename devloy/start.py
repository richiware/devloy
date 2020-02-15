# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

from .projects_info import ProjectsInfo


class StartCommand:
    logger = None
    projects_info = {}

    def __init__(self, logger, projects_info):
        self.logger = logger
        self.projects_info = projects_info


def add_subparser(subparser):
    start_parser = subparser.add_parser('start', help='start help')
    start_parser.add_argument(
            '-D', '--all-deps', action='store_true',
            help='Instead of inner-join between dependencies of "colcon.pkg" and "{project_name}.repos",\
                    a left-join will be done and use all dependencies')
    start_parser.set_defaults(func=start_verb_init)


def start_verb_init(args, defaults, logger):
    """
    Starting point of the start command

    Logic:

    * Create command using arguments
    * Find projects information:
        * Get project:
            * Try to read colcon.pkg
            * Try to get repository name

    :returns: The return code
    """
    arguments = vars(args)

    # Get projects information
    projects_info = ProjectsInfo(logger, arguments['all_deps'], defaults.search_paths)
    command = StartCommand(logger, projects_info.get_projects_info())

    del command
