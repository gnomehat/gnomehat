#!/usr/bin/env python

from setuptools import setup

setup(name='gnomehat',
        version='0.2.1',
        description='GnomeHat makes it easy to run experiments.',
        author='Larry Neal',
        author_email='nealla@lwneal.com',
        packages=[
            'gnomehat',
            'gnomehat/server'
        ],
        package_data={
            'gnomehat': ['templates/*', 'static/*', 'static/*/*']
        },
        scripts=['scripts/gnomehat_server',
                 'scripts/gnomehat_worker',
                 'scripts/gnomehat_run',
                 'scripts/gnomehat_cleanup',
                 'scripts/gnomehat'],
      install_requires=[
          "requests",
          "flask",
      ],
)
