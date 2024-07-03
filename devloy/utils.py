# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

import subprocess


def docker_container_name(project_name, branch):
    return 'dev_{}_{}'.format(project_name, branch).replace('/', '-')


def exists_docker_container(container_name):
    exists = False
    docker_ps_proc = subprocess.Popen(
            'docker ps -q --all -f name={}'.format(container_name),
            stdout=subprocess.PIPE,
            shell=True)
    docker_ps_proc.wait()
    if 0 == docker_ps_proc.returncode:
        exists = docker_ps_proc.stdout.readline().decode('utf-8').rstrip() != ''

    return exists


def is_running_docker_container(container_name):
    running = False
    docker_ps_proc = subprocess.Popen(
            'docker ps -q -f name={}'.format(container_name), # Problem with similar names
            stdout=subprocess.PIPE,
            shell=True)
    docker_ps_proc.wait()
    if 0 == docker_ps_proc.returncode:
        running = docker_ps_proc.stdout.readline().decode('utf-8').rstrip() != ''

    return running


def deduce_image(arguments, defaults):
    image = 'ubuntu:latest'

    if arguments.image:
        image = arguments.image[0]
    elif defaults.docker.image:
        image = defaults.docker.image

    return image
