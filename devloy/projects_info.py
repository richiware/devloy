# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

import subprocess
from pathlib import Path

import yaml


class ProjectsInfo:
    projects_dir = [(None, '.')]  # (project name, project dir)
    projects_info = {}
    all_deps = False
    search_paths = []

    def __init__(self, logger, all_deps, search_paths):
        self.logger = logger
        self.all_deps = all_deps
        self.search_paths = search_paths

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
        for search_path in self.search_paths:
            repo_path = Path(search_path) / repository
            if worktree:
                worktree_path = repo_path / worktree
                if worktree_path.is_dir():
                    return worktree_path
            else:
                worktree_path = repo_path / 'master'
                if worktree_path.is_dir():
                    return worktree_path
            if repo_path.is_dir():
                return repo_path

            return None

    def process_project_deps(self, project_name, project_dir, colcon_deps):
        """
        Get dependencies information, and store them to be processed.
        """
        self.logger.debug('  Processing dependencies of {}'.format(project_name))
        dependencies = colcon_deps

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
                repo_dir = self.find_dep_dir(dependency, worktree)
                if (repo_dir and
                        self.projects_info.get(dependency) is None and
                        not any(dependency in i for i in self.projects_dir)):
                    self.projects_dir.append((dependency, repo_dir))

            if self.all_deps:
                for repository in repositories:
                    if repository != project_name:
                        worktree = None
                        if 'version' in repository:
                            worktree = repository['version']
                        repo_dir = self.find_dep_dir(repository, worktree)
                        if (repo_dir and
                                self.projects_info.get(repository) is None and
                                not any(repository in i for i in self.projects_dir)):
                            self.projects_dir.append((repository, repo_dir))

    def process_project_info(self, project_name, project_dir):
        """
        Get information about the project and process it
        :returns:
        """
        assert(project_dir is not None)
        self.logger.debug('  Processing directory {}'.format(project_dir))
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

        if get_project_name is None:
            # Trying to get project name from git repository name
            get_project_name = self.get_repo_name(str(get_project_dir))
            if get_project_name:
                self.logger.debug('    Trying to get repo name... found {}'.format(get_project_name))
            else:
                self.logger.debug('    Trying to get repo name... not found')
                return

        if get_project_name is None:
            self.error('Cannot get project name for directory {}'.format(project_dir))
            return

        self.projects_info[get_project_name] = str(get_project_dir)
        self.process_project_deps(get_project_name, get_project_dir, colcon_project_deps)
        return

    def get_projects_info(self):
        self.logger.debug('Getting projects information...')
        # For each known directory. Projects directories could be increased getting infor about projects.
        while 0 < len(self.projects_dir):
            project_search_info = self.projects_dir.pop(0)
            self.process_project_info(project_search_info[0], project_search_info[1])

        return self.projects_info
