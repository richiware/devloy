# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

import shutil
import subprocess

import yaml

from .projects_info import ProjectsInfo
from .utils import (docker_container_name, exists_docker_container,
                    is_running_docker_container)


class StopCommand:
    container_name = None
    logger = None

    def __init__(self, container_name, logger):
        self.container_name = container_name
        self.logger = logger
        self.logger.debug('Stopping development environment {}'.format(container_name))

    def get_docker_container_info(self):
        docker_inspect_proc = subprocess.Popen(
                'docker inspect {}'.format(self.container_name),
                stdout=subprocess.PIPE,
                shell=True)

        docker_inspect_proc.wait()
        if 0 == docker_inspect_proc.returncode:
            return yaml.safe_load(docker_inspect_proc.stdout)
        return None

    def remove_tmp_directories(self, docker_info):
        if docker_info[0]['Mounts']:
            mounts = docker_info[0]['Mounts']

            for mount in mounts:
                destination = mount['Destination']
                if 'build' == destination[len(destination) - 5: len(destination)]:
                    shutil.rmtree(mount['Source'])
                elif 'install' == destination[len(destination) - 7: len(destination)]:
                    shutil.rmtree(mount['Source'])

    def remove_container(self):
        if is_running_docker_container(self.container_name):
            subprocess.call('docker stop {}'.format(self.container_name), shell=True)
        subprocess.call('docker rm {}'.format(self.container_name), shell=True)
        return True

    def stop_docker_container(self):
        if exists_docker_container(self.container_name):
            # Get info about container:
            docker_info = self.get_docker_container_info()
            if self.remove_container() and docker_info:
                self.remove_tmp_directories(docker_info)
        else:
            self.logger.debug('Development environment {} was not started'.format(self.container_name))


def add_subparser(subparser):
    start_parser = subparser.add_parser('stop', help='stop help')
    start_parser.set_defaults(func=stop_verb_init)


def stop_verb_init(args, defaults, logger):
    """
    Starting point of the stop command
    """
    # Get projects information
    projects_info = ProjectsInfo(logger, False, [], defaults.search_paths)

    # Get main project info to detect if docker container is already running.
    project_name, branch = projects_info.get_main_project_info()
    command = StopCommand(docker_container_name(project_name, branch), logger)

    command.stop_docker_container()

    del command
