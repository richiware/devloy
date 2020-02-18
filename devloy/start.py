# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path

from .projects_info import ProjectsInfo
from .utils import (deduce_image, docker_container_name,
                    exists_docker_container, is_running_docker_container)


class StartCommand:
    container_name = None
    image = None
    defaults = None
    logger = None
    projects_info = {}
    use_tmp = False

    def __init__(self, container_name, image, logger, defaults, use_tmp):
        self.container_name = container_name
        self.image = image
        self.defaults = defaults
        self.logger = logger
        self.use_tmp = use_tmp
        self.logger.debug('Starting development environment {}'.format(container_name))

    def exists_docker_container(self):
        return exists_docker_container(self.container_name)

    def is_running_docker_container(self):
        return is_running_docker_container(self.container_name)

    def prepare_call(self, projects_info):
        docker_args = ['docker', 'run', '-ti', '--name', self.container_name]
        if self.defaults.docker.cap_add:
            docker_args.append('--cap-add={}'.format(self.defaults.docker.cap_add))
        if self.defaults.docker.net:
            docker_args.append('--net={}'.format(self.defaults.docker.net))
        if self.defaults.docker.security_opt:
            docker_args.append('--security-opt={}'.format(self.defaults.docker.security_opt))
        if self.defaults.docker.user_env:
            docker_args.append('-u')
            docker_args.append('{}:{}'.format(os.getuid(), os.getgid()))
        for env in self.defaults.docker.env:
            docker_args.append('-e')
            docker_args.append(env)
        for volume in self.defaults.docker.volumes:
            docker_args.append('-v')
            docker_args.append(volume)

        ccdb_env_string = ''

        # Project directories
        for project in projects_info:
            info = projects_info.get(project)
            docker_args.append('-v')
            docker_args.append('{}:{}'.format(info[0], info[1]))
            ccdb_env_string += '{}:{},'.format(info[0], info[1])

        # Building directories
        if self.use_tmp:
            if self.defaults.docker.build_tmp_dir:
                docker_args.append('-v')
                build_dir = Path(self.defaults.docker.build_tmp_dir.replace(
                    '${CONTAINER_NAME}', self.container_name)).absolute()
                docker_args.append('{}:/home/{}/workspace/build'.format(
                    str(build_dir),
                    self.defaults.username))
                ccdb_env_string += '{}:/home/{}/workspace/build,'.format(
                    str(build_dir),
                    self.defaults.username)
                if not build_dir.exists():
                    build_dir.mkdir(parents=True)
            if self.defaults.docker.install_tmp_dir:
                docker_args.append('-v')
                install_dir = Path(self.defaults.docker.install_tmp_dir.replace(
                    '${CONTAINER_NAME}', self.container_name)).absolute()
                docker_args.append('{}:/home/{}/workspace/install'.format(
                    install_dir,
                    self.defaults.username))
                ccdb_env_string += '{}:/home/{}/workspace/install,'.format(
                    str(install_dir),
                    self.defaults.username)
                if not install_dir.exists():
                    install_dir.mkdir(parents=True)
        else:
            if self.defaults.docker.build_dir:
                docker_args.append('-v')
                build_dir = Path(self.defaults.docker.build_dir.replace(
                    '${CONTAINER_NAME}', self.container_name)).absolute()
                docker_args.append('{}:/home/{}/workspace/build'.format(
                    build_dir,
                    self.defaults.username))
                ccdb_env_string += '{}:/home/{}/workspace/build,'.format(
                    str(build_dir),
                    self.defaults.username)
                if not build_dir.exists():
                    build_dir.mkdir(parents=True)
            if self.defaults.docker.install_dir:
                docker_args.append('-v')
                install_dir = Path(self.defaults.docker.install_dir.replace(
                    '${CONTAINER_NAME}', self.container_name)).absolute()
                docker_args.append('{}:/home/{}/workspace/install'.format(
                    install_dir,
                    self.defaults.username))
                ccdb_env_string += '{}:/home/{}/workspace/install,'.format(
                    str(install_dir),
                    self.defaults.username)
                if not install_dir.exists():
                    install_dir.mkdir(parents=True)

        # Environment variables for CCDB
        docker_args.append('-e')
        docker_args.append('CCDB_WORKTREE=')
        docker_args.append('-e')
        docker_args.append('CCDB_WORKTREE_APPLICATION={}'.format(ccdb_env_string))

        # Append docker image
        docker_args.append(self.image)

        return docker_args

    def start_docker_container(self, projects_info):
        docker_args = self.prepare_call(projects_info)
        print(docker_args)
        os.execvp('docker', docker_args)

    def exec_docker_container(self):
        if not self.is_running_docker_container():
            os.execvp('docker', ['docker', 'start', '-i', self.container_name])
        else:
            os.execvp('docker', ['docker', 'exec', '-ti', self.container_name, '/bin/bash'])


def add_subparser(subparser, defaults):
    start_parser = subparser.add_parser('start', help='start help')
    start_parser.add_argument(
            '-D', '--all-deps', action='store_true',
            help='Instead of inner-join between dependencies of "colcon.pkg" and "{project_name}.repos",\
                    a left-join will be done and use all dependencies')
    start_parser.add_argument(
            '-t', '--tmp', action='store_true',
            help='Instead of use the build-dir, it will use it temporary version (build-tmp-dir)')
    start_parser.add_argument(
            '-r', '--repo', nargs='*',
            help='List of extra repositories to be included. They will be searched as usually. Format: (repo[:branch])')
    start_parser.add_argument(
            'image', nargs=1, default=defaults.docker.image,
            help='Docker image to be used.')
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
    """
    image = deduce_image(args, defaults)

    # Get projects information
    projects_info = ProjectsInfo(logger, args.all_deps, args.repo, defaults.search_paths)

    # Get main project info to detect if docker container is already running.
    project_name, branch = projects_info.get_main_project_info()
    command = StartCommand(docker_container_name(project_name, branch), image, logger, defaults, args.tmp)

    if not command.exists_docker_container():
        command.start_docker_container(projects_info.get_projects_info())
    else:
        command.exec_docker_container()

    del command
