# Copyright 2020 Ricardo González
# Licensed under the Apache License, Version 2.0

"""
This command generates an unique compile command database from a collective construction (colcon).
Also it is able to manage git worktree environments.
"""
import argparse
import glob
import logging
import os
import shutil
import subprocess
from pathlib import Path

from fcache.cache import FileCache

cache = None
logger = None


def parse_arguments(args):
    global logger
    parser = argparse.ArgumentParser(description="Tool for retrieving the compile command database")
    parser.add_argument(
            '--debug',
            action='store_true',
            help='Print debug info.'
    )
    options = vars(parser.parse_args(args))

    # Set log level
    if options['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


def generate_compile_command():
    # Generate the compile_commands.json
    find_proc = subprocess.Popen(
            'find build -iname compile_commands.json -print0 | grep -z . | xargs -0',
            stdout=subprocess.PIPE, shell=True)
    find_proc.wait()
    list_files = find_proc.stdout.readline().decode('utf-8').rstrip()
    find_proc.communicate()
    retcode = find_proc.returncode

    if retcode == 0 and len(list_files) > 0:
        subprocess.call('jq -s add {} > compile_commands.json'.format(list_files), shell=True)
        list_project_dirs = list_files.replace('build/', '').replace('/compile_commands.json', '').split()
        for project_dir in list_project_dirs:
            logger.debug('\tproject: {}'.format(project_dir))
        return list_project_dirs

    return None


def get_project_from_colcon():
    global logger
    logger.debug('Getting projects from colcon list')
    colcon_list = []
    # Get list of project from command 'colcon list'.
    colcon_list_proc = subprocess.Popen(
            'colcon list',
            stdout=subprocess.PIPE, shell=True)
    colcon_list_proc.wait()
    project_info = colcon_list_proc.stdout.readline()
    while project_info:
        logger.debug('\tproject: {}'.format(project_info.decode('utf-8').rstrip()))
        colcon_list.append(project_info.decode('utf-8').rstrip())
        project_info = colcon_list_proc.stdout.readline()

    colcon_list_proc.communicate()
    retcode = colcon_list_proc.returncode

    if retcode == 0:
        return colcon_list

    return None


def find_git_directory(base_dir):
    until_dir = os.getcwd()
    while base_dir != until_dir and not glob.glob(base_dir + '/.git'):
        base_dir = os.path.dirname(base_dir)

    if base_dir != until_dir:
        return Path(base_dir + '/.git').resolve()

    return None


def get_worktree_for_project(project_info):
    global logger
    logger.debug('Getting worktree configuration to {}'.format(project_info))
    # Find .git directory
    git_dir = find_git_directory(project_info[1])
    if not git_dir:
        logger.debug("Warning: cannot find Git dir for project {}".format(project_info[0]))
        return None
    logger.debug('\tFound git dir: {}'.format(git_dir))
    git_project_dir = str(git_dir).replace('/.git', '')
    logger.debug('\tFound project dir: {}'.format(git_project_dir))

    # Get branch for the project
    if git_dir.is_file():
        git_dir_file = open(git_dir, 'r')
        git_worktree_dir = git_dir_file.readline()
        git_worktree_dir = git_worktree_dir.replace('gitdir:', '').rstrip()
        project_branch = Path(git_worktree_dir).name
    else:
        git_proc = subprocess.Popen(
                'cd {} && git branch'.format(project_info[1]),
                stdout=subprocess.PIPE, shell=True)
        git_proc.wait()
        project_branch = git_proc.stdout.readline().decode('utf-8').rstrip()
        git_proc.communicate()
        retcode = git_proc.returncode

        if retcode != 0:
            logger.debug("Warning: cannot get Git branch for project {}".format(project_info[0]))
            return None

    logger.debug('\tFound project branch: {}'.format(project_branch))

    # Calculate rest of project dir since git_dir.
    project_dir = Path(project_info[1] + '/dummy')
    coincidence_project_dir = None
    for path in reversed(project_dir.parents):
        if not path == Path('.'):
            if not str(path) in str(git_dir):
                break
            coincidence_project_dir = path

    rest_of_project_dir = str(project_dir.parent).replace(str(coincidence_project_dir), '')

    # Returned tuple (git_dir, branch, rest of project dir)
    return (git_project_dir, project_branch, rest_of_project_dir)


def apply_worktree_env(list_project_dirs):
    global cache

    colcon_list = None
    sed_arguments = []
    dirs_to_copy = []

    for project_dir in list_project_dirs:
        # Search in cache.
        if project_dir in cache:
            project_info = cache[project_dir]
            logger.debug('Retrieved from cache: {} - {}'.format(
                project_dir,
                project_info
            ))

        else:
            if not colcon_list:
                colcon_list = get_project_from_colcon()
            project_info_l = list(filter(lambda proj: project_dir + '\t' in proj, colcon_list))
            project_info_l = ''.join(project_info_l).split('\t')
            dirs_to_copy.append(project_info_l[1])
            project_info = get_worktree_for_project(project_info_l)

        if project_info:
            sed_arguments.append('-e')
            sed_arguments.append('s+{}{}+{}/{}{}+g'.format(
                project_info[0],
                project_info[2],
                project_info[0],
                project_info[1],
                project_info[2]
            ))
            dirs_to_copy.append(project_info[0])
            # Update cache
            logger.debug('Storing in cache: {} - {}'.format(
                project_dir,
                project_info
            ))
            cache[project_dir] = project_info

    logger.debug('\tCalling sed argument: {}'.format(
        ' '.join(['sed'] + sed_arguments + ['compile_commands.json', '>', 'ccdb.json'])
    ))
    subprocess.call(' '.join(['sed'] + sed_arguments + ['compile_commands.json', '>', 'ccdb.json']), shell=True)

    # Copy compile command database to all projects
    dirs_to_copy = set(dirs_to_copy)
    for dir_to_copy in dirs_to_copy:
        shutil.copy2('ccdb.json', dir_to_copy + '/compile_commands.json')
    os.remove('ccdb.json')


def apply_worktree_env_using_envvar(env_var):
    dirs_to_copy = []
    list_substitutions = env_var.split(',')
    sed_arguments = []

    for substitution in list_substitutions:
        directories = substitution.split(':')
        if 2 == len(directories) and directories[0] != '' and directories[1] != '':
            origin = directories[1]
            dest = directories[0]
            sed_arguments.append('-e')
            sed_arguments.append('s+{}/+{}/+g'.format(origin, dest))
            if 'build' != origin[len(origin) - 5: len(origin)] and 'install' != origin[len(origin) - 7: len(origin)]:
                dirs_to_copy.append(directories[1])

    command = ' '.join(
            ['sed'] +
            sed_arguments +
            ['compile_commands.json', '>', 'ccdb.json'])
    logger.debug('\tCalling sed argument: {}'.format(command))
    subprocess.call(command, shell=True)

    # Copy compile command database to all projects
    dirs_to_copy = set(dirs_to_copy)
    for dir_to_copy in dirs_to_copy:
        shutil.copy2('ccdb.json', dir_to_copy + '/compile_commands.json')
    os.remove('ccdb.json')


def main(argv=None):
    """
    Logic:
        * Generate the unique compile command database.
        * Get worktree branches and changes urls in compile command database
    """
    global logger, cache

    # Getting environment variables
    ccdb_worktree_env = os.environ.get('CCDB_WORKTREE')
    ccdb_worktree_apply_env = os.environ.get('CCDB_WORKTREE_APPLICATION')

    # Create a custom logger
    logger = logging.getLogger(__name__)
    # - Create handlers
    c_handler = logging.StreamHandler()
    # - Create formatters and add it to handlers
    c_format = '[%(asctime)s][ccdb][%(levelname)s] %(message)s'
    c_format = logging.Formatter(c_format)
    c_handler.setFormatter(c_format)
    # - Add handlers to the logger
    logger.addHandler(c_handler)

    # Parse arguments
    parse_arguments(args=argv)

    # Generate unique compile command database
    logger.debug('Generating compile command database')
    list_project_dirs = generate_compile_command()

    if not list_project_dirs:
        exit(0)

    if ccdb_worktree_env is not None:
        if ccdb_worktree_apply_env:
            apply_worktree_env_using_envvar(ccdb_worktree_apply_env)
        else:
            # Load cache
            cache = FileCache('ccdb')
            logger.debug('Applying worktree configuration to compile command database')
            apply_worktree_env(list_project_dirs)
            cache.close()

# Copiar a todos los projectos o solo al dicho por la variable de entorno
