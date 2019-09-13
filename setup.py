#!/usr/bin/env python

from setuptools import setup
from setuptools.command.install import install
import os
import requests
import subprocess


setup(name='gnomehat',
    version='0.7.16',
    description='GnomeHat: easy experiment control',
    author='Larry Neal',
    author_email='nealla@lwneal.com',
    packages=[
        'gnomehat',
        'gnomehat/server',
        'gnomehat/console',
    ],
    package_data={
        'gnomehat': [
            'templates/*',
            'static/js/*.js',
            'static/fonts/*.otf',
            'static/fonts/*.svg',
            'static/fonts/*.woff',
            'static/fonts/*.woff2',
            'static/fonts/*.ttf',
            'static/fonts/*.otf',
            'static/fonts/*.eot',
            'static/css/*.css',
            'static/images/*.png',
            'static/images/*.jpg',
        ]
    },
    scripts=[
        'scripts/gnomehat',
        'scripts/gnomehat_server',
        'scripts/gnomehat_worker',
        'scripts/gnomehat_cleanup',
        'scripts/gnomehat_install_standalone_python',
        'scripts/gnomehat_websocket',
        'scripts/gnomehat_doctor',
    ],
    install_requires=[
        "requests",
        "flask",
        "pytz",
        "websockets",
        "docopt",
    ],
    python_requires='>3',
)
