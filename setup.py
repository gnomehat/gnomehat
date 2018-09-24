#!/usr/bin/env python

from setuptools import setup
from setuptools.command.install import install
import os
import requests
import subprocess

WEBSOCKETD_URL = 'https://github.com/joewalnes/websocketd/releases/download/v0.3.0/websocketd-0.3.0-linux_amd64.zip'
WEBSOCKETD_FILENAME = 'websocketd-0.3.0-linux_amd64.zip'
WEBSOCKETD_CHECKSUM = '03b8d90b4ac1f58469965c133cf3dd9c43dc0811e525b2319df578e7057db5b4'

class PostInstallCommand(install):
    def run(self):
        print('Installing websocketd from {}'.format(WEBSOCKETD_URL))
        install_websocketd('~/bin')
        install.run(self)


def install_websocketd(bin_dir):
    bin_dir = os.path.expanduser(bin_dir)
    os.makedirs(bin_dir, exist_ok=True)
    filepath = os.path.join(bin_dir, WEBSOCKETD_FILENAME)
    if not os.path.exists(os.path.join(bin_dir, 'websocketd')):
        subprocess.run(['wget', '--no-clobber', '-P', bin_dir, WEBSOCKETD_URL])
        subprocess.run(['unzip', '-d', bin_dir, filepath])


setup(name='gnomehat',
        version='0.5.5',
        description='GnomeHat: easy experiment control',
        author='Larry Neal',
        author_email='nealla@lwneal.com',
        packages=[
            'gnomehat',
            'gnomehat/server'
        ],
        package_data={
            'gnomehat': ['templates/*',
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
        scripts=['scripts/gnomehat_server',
                 'scripts/gnomehat_worker',
                 'scripts/gnomehat_run',
                 'scripts/gnomehat_cleanup',
                 'scripts/gnomehat'],
      install_requires=[
          "requests",
          "flask",
          "pytz",
      ],
      cmdclass={
        'install': PostInstallCommand,
      },
)
