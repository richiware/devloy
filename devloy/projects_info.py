# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

import subprocess
from pathlib import Path

import yaml


class ProjectsInfo:
    projects_dir = [(None, '.', None)]  # (project name, project dir)
    projects_info = {}
    all_deps = False
    search_paths = []

    def __init__(self, logger, all_deps, extra_repos, search_paths):
        self.logger = logger
        self.all_deps = all_deps
        self.search_paths = search_paths

        for repo in extra_repos:
            repo_info = repo.split(':')
            repo_name = repo_info[0]
            branch = None
            if 1 < len(repo_info):
                branch = repo_info[1]
            repo_dir, branch = self.find_dep_dir(repo_name, branch)
            if repo_dir:
                self.logger.debug('    Adding extra repo {} - {}'.format(repo_name, repo_dir))
                self.projects_dir.append((repo_name, repo_dir, branch))

    def read_colcon_pkg(self, colcon_pkg_path):
        """
        Read the content of a colcon.pkg file.
        :returns: package name , list of project dependencies
        """
        colcon_pkg_content = colcon_pkg_path.read_text()
        yaml_content = yaml.safe_load(colcon_pkg_content)

        if 'name' not in yaml_content:
            return None, None

        return yaml_content['name'], yaml_content['dependencies'] if 'dependencies' in yaml_content else None

    def get_repo_name(self, project_dir):
        """
        Get the project name from the Git repository url.
        :returns: The name of the Git repository.
        """
        git_remote_proc = subprocess.Popen(
                'cd {} && git remote get-url origin'.format(project_dir),
                stdout=subprocess.PIPE,
                shell=True)
        git_remote_proc.wait()
        if 0 != git_remote_proc.returncode:
            return None

        url = git_remote_proc.stdout.readline().decode('utf-8').rstrip()

        try:
            url = url[:url.rindex('.git')]
        except ValueError:
            pass

        try:
            url = url[url.rindex('/') + 1:]
        except ValueError:
            pass

        return url

    def find_dep_dir(self, repository, worktree):
        """
        :return: repository directory, suffix
        """
        for search_path in self.search_paths:
            repo_path = Path(search_path) / repository
            if worktree:
                worktree_path = repo_path / worktree
                if worktree_path.is_dir():
                    return worktree_path, worktree
            else:
                worktree_path = repo_path / 'master'
                if worktree_path.is_dir():
                    return worktree_path, 'master'
            if repo_path.is_dir():
                return repo_path, None

            return None, None

    def get_project_suffix(self, project_name, project_dir):
        """
        Get the project branch and verify that it is used in a worktree environment.
        :returns: The suffix used in the project's directory
        """
        suffix = ''
        git_branch_proc = subprocess.Popen(
                'cd {} && git branch --show-current'.format(project_dir),
                stdout=subprocess.PIPE,
                shell=True)
        git_branch_proc.wait()
        if 0 == git_branch_proc.returncode:
            suffix = git_branch_proc.stdout.readline().decode('utf-8').rstrip()

        directory_suffix = ''
        try:
            directory_suffix = project_dir[project_dir.index(project_name) + len(project_name) + 1:]
        except Exception:
            pass

        if directory_suffix != suffix:
            self.logger.warning('Git branch ({}) differs from url suffix ({}). Using latest one.'.format(
                suffix, directory_suffix))
            suffix = directory_suffix

        return suffix if suffix else None

    def process_project_deps(self, project_name, project_dir, colcon_deps):
        """
        Get dependencies information, and store them to be processed.
        """
        self.logger.debug('  Processing dependencies of {}'.format(project_name))
        num_colcon_deps = len(colcon_deps) if colcon_deps else 0
        dependencies = colcon_deps if colcon_deps else []
        initial_pos_projects_dir = len(self.projects_dir)

        # Use {project_name}.repos to get info about dependencies
        repos_path = project_dir / (project_name + '.repos')
        if repos_path.is_file():
            repos_content = repos_path.read_text()
            yaml_content = yaml.safe_load(repos_content)
            repositories = yaml_content['repositories']

            while 0 < len(dependencies):
                dependency = dependencies.pop(0)
                repository = None
                worktree = None
                try:
                    repository = repositories.pop(dependency)
                    if 'version' in repository:
                        worktree = repository['version']
                except Exception:
                    pass
                repo_dir, suffix = self.find_dep_dir(dependency, worktree)
                if (repo_dir and
                        self.projects_info.get(dependency) is None and
                        not any(dependency in i for i in self.projects_dir)):
                    self.projects_dir.append((dependency, repo_dir, suffix))

            if 0 == num_colcon_deps or self.all_deps:
                for name in repositories:
                    if name != project_name:
                        repository = repositories.get(name)
                        worktree = None
                        if 'version' in repository:
                            worktree = repository['version']
                        repo_dir, suffix = self.find_dep_dir(name, worktree)
                        if (repo_dir and
                                self.projects_info.get(name) is None and
                                not any(name in i for i in self.projects_dir)):
                            self.projects_dir.append((name, repo_dir, suffix))

            self.logger.debug('    Dependencies:')
            while initial_pos_projects_dir < len(self.projects_dir):
                self.logger.debug('      {}: {}'.format(
                    self.projects_dir[initial_pos_projects_dir][0],
                    self.projects_dir[initial_pos_projects_dir][1]
                    ))
                initial_pos_projects_dir += 1

    def get_project_info(self, project_name, project_dir, suffix):
        """
        Get information about the project and process it. The returned info about each project is:

            ( name of the project, directory of the project, suffix in the url (suffix == branch if using worktrees) )

        Logic:
            * Getting information from a colcon.pkg file: project's name (if not known) and project's dependencies.
            * If project's name is not known, try to get for Git repository url.
        :returns:
        """
        assert(project_dir is not None)
        get_project_name = project_name
        get_project_dir = Path(project_dir).absolute()

        # Trying to get colcon.pkg file.
        colcon_pkg_path = get_project_dir / 'colcon.pkg'
        colcon_project_deps = None
        if colcon_pkg_path.is_file():
            self.logger.debug('    Trying to get colcon.pkg... found')
            colcon_project_name, colcon_project_deps = self.read_colcon_pkg(colcon_pkg_path)
            if colcon_project_name:
                if get_project_name and get_project_name != colcon_project_name:
                    self.logger.warning(
                            'Incompatibility: {} project contains a colcon.pkg with name {}'
                            .format(get_project_name, colcon_project_name))
                elif get_project_name is None:
                    get_project_name = colcon_project_name
        else:
            self.logger.debug('    Trying to get colcon.pkg... not found')

        # Trying to get project name from git repository name
        if get_project_name is None:
            get_project_name = self.get_repo_name(str(get_project_dir))
            if get_project_name:
                self.logger.debug('    Trying to get repo name... found {}'.format(get_project_name))
            else:
                self.logger.debug('    Trying to get repo name... not found')
                return None, None, None, None

        if get_project_name is None:
            self.logger.error('Cannot get project name for directory {}'.format(project_dir))
            return None, None, None, None

        # If processing directory '.', try to find its suffix (branch).
        if not suffix and project_dir == '.':
            suffix = self.get_project_suffix(get_project_name, str(get_project_dir))

        return get_project_name, get_project_dir, suffix, colcon_project_deps

    def process_project_info(self, project_name, project_dir, suffix):
        """
        Call to get project info, store it and its dependencies to be processed too.

        :returns:
        """
        assert(project_dir is not None)
        self.logger.debug('  Processing directory {}'.format(project_dir))

        get_project_name, get_project_dir, suffix, colcon_project_deps = self.get_project_info(
                project_name, project_dir, suffix)

        if get_project_name:
            self.projects_info[get_project_name] = (
                    str(get_project_dir),
                    str(get_project_dir).replace('/' + suffix, '')
                    )
            self.logger.debug('    Registered ({}: {}, {})'.format(get_project_name, str(get_project_dir), suffix))
            self.process_project_deps(get_project_name, get_project_dir, colcon_project_deps)

        return

    def get_projects_info(self):
        self.logger.debug('Getting projects information...')

        # For each known directory. Projects directories could be increased getting infor about projects.
        while 0 < len(self.projects_dir):
            project_search_info = self.projects_dir.pop(0)
            self.process_project_info(project_search_info[0], project_search_info[1], project_search_info[2])

        return self.projects_info

    def get_main_project_info(self):
        if 0 < len(self.projects_dir) and self.projects_dir[0][1] == '.':
            project_info = self.projects_dir.pop(0)
            get_project_name, get_project_dir, suffix, deps = self.get_project_info(
                    project_info[0], project_info[1], project_info[2])
            self.projects_dir.append((get_project_name, str(get_project_dir), suffix))
            return get_project_name, suffix

        return None, None
