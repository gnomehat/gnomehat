#!/usr/bin/env python3
import json
import os
import sys
import subprocess
import socket
import time
import tempfile
from gnomehat import sysinfo
from gnomehat import hostinfo
from gnomehat.file_input import read_directory_name, read_option

from gnomehat.console.args import print_usage, parse_gnomehat_args


def load_config_file():
    config_path = os.path.expanduser('~/.gnomehat')
    try:
        cfg = json.loads(open(config_path).read())
        if 'experiments_dir' not in cfg:
            return False
    except:
        return False
    return cfg


def save_config_file(config):
    config_path = os.path.expanduser('~/.gnomehat')
    print('Saving JSON config {} to file {}'.format(config, config_path))
    with open(config_path, 'w') as fp:
        fp.write(json.dumps(config, indent=2))


def prompt_create_experiments_dir():
    print('\n')
    print('Hello!')
    print('It looks like this is your first time running gnomehat')
    print('(The GNOMEHAT_DIR variable has not been set.)')
    print('\n')
    print('Please choose a directory where your experiments should be stored.')
    print('Enter a directory name (eg. /home/username/experiments)')
    experiments_dir = read_directory_name()
    print('\n')

    print('Now using {} as the GNOMEHAT_DIR'.format(experiments_dir))
    save_config_file({'experiments_dir': experiments_dir})
    print("")

    print('Checking for CUDA/CuDNN installation...')
    result = subprocess.run('gnomehat_doctor')
    if result.returncode != 0:
        print('CUDA or CuDNN is not currently installed. Install them now?')
        selection = read_option({
            'install': 'Download and install CUDA and CUDNN',
            'nothing': 'Do nothing',
        })
        if selection == 'install':
            subprocess.run(['sudo', 'gnomehat_install_cuda_cudnn'])
            subprocess.run('gnomehat_doctor')
    else:
        print('CUDA and CuDNN are available')

    print("")
    print('Which way would you like Gnomehat to run Python?')
    print("    (If you're not sure, select option #1)")
    print("")
    selection = read_option({
        'miniconda': 'Run Gnomehat with Python 3.6 at {}/env'.format(experiments_dir),
        'nothing': 'Use your current Python at: {}'.format(which_python()),
    })
    if selection == 'nothing':
        print('Gnomehat will use the current Python: {}'.format(which_python()))
    else:
        print('Installing Gnomehat-only Python to {}/env'.format(experiments_dir))
        install_miniconda_python(experiments_dir)
        print('Gnomehat will use Miniconda Python at {}'.format(experiments_dir))
    print("")

    return experiments_dir


def install_miniconda_python(experiments_dir):
    cmd = ['gnomehat_install_standalone_python', os.path.join(experiments_dir, 'env')]
    subprocess.run(cmd)


def which_python():
    return str(subprocess.check_output(['which', 'python']), 'utf').strip()

