# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

import getpass
from pathlib import Path

import yaml


class DockerDefaults:
    build_dir = None
    build_tmp_dir = None
    cap_add = []
    groups = []
    env = []
    image = None
    install_dir = None
    install_tmp_dir = None
    net = None
    privileged = None
    security_opt = None
    user_env = False
    volumes = []
    shm_size = None
    extra_args = []


class Defaults:
    docker = DockerDefaults()
    search_paths = []
    username = ''

    def get_user_name(self):
        self.username = getpass.getuser()

    def __init__(self):
        self.get_user_name()

        defaults_path = Path.home() / '.config/devloy/defaults.yaml'
        if not defaults_path.is_file():
            return

        defaults_content = defaults_path.read_text()
        yaml_content = yaml.safe_load(defaults_content)
        if 'search-paths' in yaml_content:
            self.search_paths = yaml_content['search-paths']
        if 'docker' in yaml_content:
            docker_config = yaml_content['docker']
            if 'run' in docker_config:
                docker_run_config = docker_config['run']
                if 'image' in docker_run_config:
                    self.docker.image = docker_run_config['image']
                if 'build-dir' in docker_run_config:
                    self.docker.build_dir = docker_run_config['build-dir']
                if 'build-tmp-dir' in docker_run_config:
                    self.docker.build_tmp_dir = docker_run_config['build-tmp-dir']
                if 'install-dir' in docker_run_config:
                    self.docker.install_dir = docker_run_config['install-dir']
                if 'install-tmp-dir' in docker_run_config:
                    self.docker.install_tmp_dir = docker_run_config['install-tmp-dir']
                if 'privileged' in docker_run_config and True == docker_run_config['privileged']:
                    self.docker.privileged = True
                if 'cap-add' in docker_run_config:
                    self.docker.cap_add = docker_run_config['cap-add']
                if 'net' in docker_run_config:
                    self.docker.net = docker_run_config['net']
                if 'security-opt' in docker_run_config:
                    self.docker.security_opt = docker_run_config['security-opt']
                if 'user-env' in docker_run_config:
                    self.docker.user_env = docker_run_config['user-env']
                if 'env' in docker_run_config:
                    self.docker.env = docker_run_config['env']
                    self.docker.env = [env.replace('${USER}', self.username) for env in self.docker.env]
                if 'volumes' in docker_run_config:
                    self.docker.volumes = docker_run_config['volumes']
                    self.docker.volumes = [volume.replace('${USER}', self.username) for volume in self.docker.volumes]
                if 'groups' in docker_run_config:
                    self.docker.groups = docker_run_config['groups']
                if 'shm-size' in docker_run_config:
                    self.docker.shm_size = docker_run_config['shm-size']
                if 'extra-args' in docker_run_config:
                    self.docker.extra_args = docker_run_config['extra-args']
