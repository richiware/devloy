#!/usr/bin/env python

from setuptools import setup

setup(
        name='devloy',
        version='0.1',
        description='Utility to deploy a developer environment using docker and colcon',
        author='Ricardo González',
        author_email='correoricky@gmail.com',
        license='Apache License, Version 2.0',
        packages=['devloy', 'ccdb'],
        entry_points={
            'console_scripts': [
                'devloy = devloy.core:main',
                'ccdb = ccdb.core:main'
                ]
            },
        install_requires=['fcache']
        )
