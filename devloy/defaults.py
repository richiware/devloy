# Copyright 2019 Ricardo González
# Licensed under the Apache License, Version 2.0

from pathlib import Path

import yaml


class Defaults:
    search_paths = []

    def __init__(self):
        defaults_path = Path.home() / '.config/devloy/defaults.yaml'
        if not defaults_path.is_file():
            return

        defaults_content = defaults_path.read_text()
        yaml_content = yaml.safe_load(defaults_content)
        if 'search-paths' in yaml_content:
            self.search_paths = yaml_content['search-paths']
